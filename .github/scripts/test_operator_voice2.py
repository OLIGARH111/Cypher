import asyncio
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
import numpy as np

from jarvis_backend.operator import Operator
from jarvis_backend.tools import ToolError
from jarvis_backend.voice.denoise import denoise
from jarvis_backend.voice.audio import decode_wav, encode_wav, AudioError
from jarvis_backend.voice import worker
from jarvis_backend.brain.actions import validate_step, PlanError


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.now=10
        self.runner=Mock(return_value={'title':'Document', 'handle':100,'pid':200,'nodes':[
            {'runtime':'1.2.3','name':'Save','type':'ControlType.Button','enabled':True,'patterns':['Invoke']}]})
        self.operator=Operator(self.runner, lambda:self.now)
        self.token=self.operator.run('operator_inspect', {'window':'Document'})['elements'][0]['target']

    def test_model_confirmed_flag_cannot_authorize_write(self):
        with self.assertRaises(ToolError):
            self.operator.run('operator_invoke',{'target':self.token,'confirmed':True})
        self.runner.assert_called_once()

    def test_observed_target_required(self):
        with self.assertRaises(ToolError):
            self.operator.run('operator_invoke',{'target':'invented'},approved=True)

    def test_approval_uses_observed_label(self):
        self.assertIn('Save — Document',self.operator.confirmation('operator_invoke',{'target':self.token}))

    def test_mutation_invalidates_snapshot(self):
        self.runner.return_value={'ok':True}
        self.operator.run('operator_invoke',{'target':self.token},approved=True)
        with self.assertRaises(ToolError):self.operator.target(self.token)

    def test_failed_mutation_cannot_reuse_target(self):
        self.runner.side_effect=ToolError('Timeout after button may have been pressed')
        with self.assertRaises(ToolError):
            self.operator.run('operator_invoke',{'target':self.token},approved=True)
        with self.assertRaises(ToolError):
            self.operator.run('operator_invoke',{'target':self.token},approved=True)
        self.assertEqual(self.runner.call_count,2)  # initial inspect plus one action

    def test_concurrent_mutations_execute_once(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        entered=threading.Event(); release=threading.Event()
        def action(request):
            entered.set()
            if not release.wait(5): raise AssertionError('Test action timed out')
            return {'ok':True}
        self.runner.side_effect=action
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.operator.run,'operator_invoke',{'target':self.token},approved=True)
            self.assertTrue(entered.wait(5))
            second=pool.submit(self.operator.run,'operator_invoke',{'target':self.token},approved=True)
            release.set()
            self.assertTrue(first.result(timeout=5)['ok'])
            with self.assertRaises(ToolError):second.result(timeout=5)
        self.assertEqual(self.runner.call_count,2)

    def test_expired_target(self):
        self.now=400
        with self.assertRaises(ToolError):self.operator.target(self.token)

    def test_text_validation(self):
        with self.assertRaises(ToolError):
            self.operator.run('operator_set_value',{'target':self.token,'text':'x'*12001},approved=True)

    def test_scheduled_mutations_are_not_allowed(self):
        with self.assertRaises(PlanError):
            validate_step({'action':'operator_invoke','args':{'target':self.token}},for_automation=True)

    def test_document_whitespace_preserved(self):
        result=validate_step({'action':'operator_set_value','args':{'target':self.token,'text':'  Title\n\nBody\n'}})
        self.assertEqual(result['args']['text'],'  Title\n\nBody\n')


class VoiceTests(unittest.TestCase):
    def test_silence_stays_silent(self):
        self.assertTrue(np.array_equal(denoise(np.zeros(16000)),np.zeros(16000)))

    def test_output_is_finite_bounded_and_same_length(self):
        x=np.random.default_rng(1).normal(0,.1,16000).astype(np.float32)
        y=denoise(x)
        self.assertEqual(y.shape,x.shape)
        self.assertTrue(np.isfinite(y).all())
        self.assertLessEqual(float(np.max(np.abs(y))),1)
        self.assertLess(float(np.mean(y*y)),float(np.mean(x*x)))

    def test_rumble_attenuated(self):
        x=(.2*np.sin(2*np.pi*40*np.arange(16000)/16000)).astype(np.float32)
        self.assertLess(np.mean(denoise(x)**2),np.mean(x*x)*.3)

    def test_invalid_samples(self):
        with self.assertRaises(ValueError):denoise(np.array([np.nan]))

    def test_truncated_audio_rejected(self):
        wav=encode_wav(b'\0\0'*16000,16000)
        with self.assertRaises(AudioError):decode_wav(wav[:-3])

    def test_neural_gate_does_not_transcribe_unrelated_audio(self):
        detector=Mock();detector.detect.return_value=False
        with patch.object(worker,'_wake_detector',detector),patch.object(worker,'transcribe_job') as asr:
            result=worker.wake_transcribe_job('unused',encode_wav(b'\0\0'*16000,16000),'ru')
        self.assertFalse(result['neural_wake'])
        asr.assert_not_called()

    def test_neural_hit_transcribes_command(self):
        detector=Mock();detector.detect.return_value=True
        with patch.object(worker,'_wake_detector',detector),patch.object(worker,'transcribe_job',return_value={'text':'Сайфер открой блокнот'}) as asr:
            result=worker.wake_transcribe_job('unused',encode_wav(b'\0\0'*16000,16000),'ru')
        self.assertTrue(result['neural_wake']);asr.assert_called_once()


class VoiceServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from jarvis_backend.voice.service import VoiceService
        from jarvis_backend.settings import VoiceSettings
        self.temp=tempfile.TemporaryDirectory()
        settings=Mock()
        settings.get.return_value=SimpleNamespace(voice=VoiceSettings(enabled=True))
        self.service=VoiceService(Path(self.temp.name),settings)
        self.service.pack.available=Mock(return_value=True)
        self.service.downloads.installed=Mock(return_value=True)
        self.service.worker.run=AsyncMock()

    async def asyncTearDown(self):
        self.service.worker.shutdown()
        self.temp.cleanup()

    async def result_for(self,text,hit):
        self.service.worker.run.return_value={'text':text,'neural_wake':hit}
        return await self.service.transcribe(b'fixture','wake')

    async def test_acoustic_name_only_survives_empty_asr(self):
        result=await self.result_for('',True)
        self.assertTrue(result['wake'])
        self.assertFalse(result['noise'])
        self.assertEqual(result['command'],'')

    async def test_hallucinated_text_is_never_a_command(self):
        result=await self.result_for('Спасибо за просмотр',True)
        self.assertTrue(result['wake'])
        self.assertEqual(result['command'],'')

    async def test_asr_name_cannot_override_negative_acoustic_gate(self):
        result=await self.result_for('Сайфер открой блокнот',False)
        self.assertFalse(result['wake'])

    async def test_acoustic_command_preserved_without_name_in_asr(self):
        result=await self.result_for('Открой блокнот',True)
        self.assertTrue(result['wake'])
        self.assertEqual(result['command'],'Открой блокнот')


if __name__ == '__main__': unittest.main()
