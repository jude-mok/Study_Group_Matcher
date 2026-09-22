pass
import contextlib
import io
import json
from pathlib import Path
import signal
import sys
import unittest
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent


class Result(unittest.TextTestResult):
    records = None

    def startTestRun(self):
        self.records = []

    def startTest(self, test):
        super().startTest(test)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Test exceeded 15 seconds')))
            signal.alarm(15)

    def stopTest(self, test):
        if hasattr(signal, 'SIGALRM'): signal.alarm(0)
        super().stopTest(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({'test':test.id(),'status':'pass'})

    def addFailure(self, test, err):
        super().addFailure(test,err)
        self.records.append({'test':test.id(),'status':'fail','reason':str(err[1])})

    def addError(self, test, err):
        super().addError(test,err)
        self.records.append({'test':test.id(),'status':'error','reason':str(err[1])})


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern='test_*.py')
    # Suppress production debug tracebacks from fixture-generated invalid tokens.
    with contextlib.redirect_stdout(io.StringIO()):
        result = unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    report = {'generated_at':datetime.now(timezone.utc).isoformat(), 'scope':'Offline API/service/WebSocket integration; Supabase replaced; no real DB or network', 'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors),'failed':len(result.failures),'errors':len(result.errors),'results':result.records}
    path = HERE.parent/'test-results'/'integration.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Report: {path}')
    sys.exit(0 if result.wasSuccessful() else 1)
