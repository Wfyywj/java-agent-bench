"""Real Java checks: narrow concurrency normalization must not hide infrastructure errors."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / 'engineering/integration/S04-spring'
CACHE = Path(os.environ.get('S04_SPRING_DEPS', '/tmp/java-agent-bench-s04-spring-deps'))


class SpringContractBoundaries(unittest.TestCase):
    def test_future_boundary_preserves_unknown_failures(self):
        jars = [CACHE / row['file'] for row in json.loads((TASK / 'dependencies.lock.json').read_text())]
        if not all(p.is_file() for p in jars):
            self.skipTest('frozen Spring dependency cache not provisioned')
        cp = ':'.join(map(str, jars))
        with tempfile.TemporaryDirectory(prefix='spring-contract-') as directory:
            temp = Path(directory)
            probe = temp / 'ContractBoundaryProbe.java'
            probe.write_text('''package bench;
import java.util.concurrent.*;
public class ContractBoundaryProbe {
    static CompletableFuture<Object> failed(Throwable error) {
        CompletableFuture<Object> f=new CompletableFuture<>();f.completeExceptionally(error);return f;
    }
    static void retained(Throwable error) throws Exception {
        try {IntegrationVerifier.orderedResult(failed(error));throw new AssertionError("not thrown");}
        catch(ExecutionException expected) {
            Throwable original=error instanceof CompletionException ? error.getCause() : error;
            if(expected.getCause()!=original)throw new AssertionError("cause changed");
        }
    }
    public static void main(String[] args) throws Exception {
        AssertionError assertion=new AssertionError("controlled barrier");
        try {IntegrationVerifier.workerResult(failed(new CompletionException(assertion)),1);
            throw new IllegalStateException("assertion lost");}
        catch(AssertionError expected) {if(expected!=assertion)throw new IllegalStateException("wrong assertion");}
        try {IntegrationVerifier.orderedResult(failed(new CompletionException(
            new IllegalStateException("Concurrent order transition"))));
            throw new IllegalStateException("contract violation lost");}
        catch(AssertionError expected) {
            if(!"per-batch serialization violated".equals(expected.getMessage()))throw expected;
        }
        retained(new IllegalStateException("unknown runtime failure"));
        retained(new java.sql.SQLException("database unavailable"));
        retained(new CompletionException(new java.sql.SQLException("wrapped database failure")));
        retained(new TimeoutException("worker infrastructure timeout"));
        try {IntegrationVerifier.workerResult(new CompletableFuture<>(),0);
            throw new AssertionError("timeout swallowed");}
        catch(TimeoutException expected) {} // Only the explicit unrelated-progress probe converts this.
        System.out.println("contract boundaries preserved");
    }
}''')
            sources = sorted((TASK / 'reference/src').rglob('*.java')) + sorted((TASK / 'regression-tests').rglob('*.java'))
            compiled = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '-source', '21', '-target', '21', '-cp', cp, '-d', str(temp), *map(str, sources), str(probe)], capture_output=True, text=True, timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run(['java', '-cp', str(temp) + ':' + cp, 'bench.ContractBoundaryProbe'], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('contract boundaries preserved', result.stdout)
