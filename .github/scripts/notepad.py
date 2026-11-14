import os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(os.environ['CYPHER_TEST_DIR'])/'backend'))
from jarvis_backend.operator import Operator
subprocess.Popen(['notepad.exe'])
op=Operator()
for i in range(20):
    windows=op.run('operator_windows',{})['windows']
    matches=[w for w in windows if 'notepad' in w['title'].lower()]
    if matches:break
    time.sleep(.5)
assert len(matches)==1,windows
snap=op.run('operator_inspect',{'window':matches[0]['title']})
items=[x for x in snap['elements'] if x['type'] in ('ControlType.Edit','ControlType.Document')]
assert len(items)==1,snap
text='Cypher Operator\r\n\r\nЭтот текст введён в Блокнот через Windows UI Automation.\r\n\r\nОперации: найти окно, прочитать элементы, заполнить поле.\r\nВерсия Cypher: 1.1.1\r\n\r\nДемонстрация в тестовой Windows.'
op.run('operator_set_value',{'target':items[0]['target'],'text':text},approved=True)
snap=op.run('operator_inspect',{'window':'Notepad'})
items=[x for x in snap['elements'] if x['type'] in ('ControlType.Edit','ControlType.Document')]
assert op.run('operator_read',{'target':items[0]['target']})['text'].strip()==text.strip()
print('PASS: Operator entered and read back text in real Windows Notepad')
