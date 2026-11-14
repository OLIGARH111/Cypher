import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import zipfile

app = Path(os.environ['CYPHER_TEST_DIR'])
sys.path.insert(0, str(app/'backend'))
from jarvis_backend.operator import Operator
from jarvis_backend.tools import ToolError

operator=Operator()
def observe():
    for attempt in range(20):
        try:
            snapshot=operator.run('operator_inspect', {'window':'Cypher Operator Fixture'})
            if snapshot['elements']: return snapshot
        except ToolError:
            pass
        time.sleep(0.5)
    raise AssertionError('UI fixture not found')

def token_for(name):
    snap=observe()
    assert not any(x['name']=='Secret field' for x in snap['elements']), 'Password field exposed'
    items=[x for x in snap['elements'] if x['name']==name]
    assert len(items)==1, (name,snap)
    return items[0]['target']

target=token_for('Document text')
try:
    operator.run('operator_set_value', {'target':target,'text':'unapproved','confirmed':True})
    raise AssertionError('Unapproved UI mutation accepted')
except ToolError:
    pass
text='Cypher Operator\r\nПроверка документа'
operator.run('operator_set_value', {'target':target,'text':text}, approved=True)
target=token_for('Document text')
assert operator.run('operator_read', {'target':target})['text'].strip()==text.strip()
target=token_for('Apply document')
operator.run('operator_invoke', {'target':target}, approved=True)
assert any(x['name']=='Applied' for x in observe()['elements'])
print('PASS: real Windows UIA inspect, protected fields, approval, text entry, read-back and button invocation',flush=True)

from jarvis_backend.voice.pack import VoicePack
from jarvis_backend.voice.worker import prepare_imports
with tempfile.TemporaryDirectory() as temp:
    pack=VoicePack(Path(temp))
    asyncio.run(pack._install())
    assert pack.progress.state=='done',pack.progress.error
    assert pack.installed()
    prepare_imports(str(pack.site))
    from jarvis_backend.voice.neural_wake import NeuralWake
    from jarvis_backend.voice.audio import decode_wav
    detector=NeuralWake()
    fixtures=Path(temp)/'fixtures'
    with zipfile.ZipFile('voice-fixtures.zip') as z:
        z.extractall(fixtures)
    for language in ['en','ru']:
        for index in range(7):
            audio=decode_wav((fixtures/f'{language}_{index}.wav').read_bytes())
            actual=detector.detect(audio)
            assert actual==(index<3),(language,index,actual)
    print('PASS: verified voice pack and 14 bilingual acoustic wake tests on Windows',flush=True)
    from jarvis_backend.voice.denoise import denoise
    import numpy as np
    assert np.array_equal(denoise(np.zeros(16000)),np.zeros(16000))
    print('PASS: Windows voice denoiser',flush=True)
