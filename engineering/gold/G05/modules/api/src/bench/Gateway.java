package bench;
import java.util.concurrent.*;
public interface Gateway extends AutoCloseable {
  Future<Integer> submit(Callable<Integer> call, boolean independent);
  Snapshot snapshot();
  void close();
  record Snapshot(int accepted,int rejected,int completed,int cancelled,int failed,
                  int slowWorkers,int slowQueueCapacity,int fastWorkers,int fastQueueCapacity) {}
}
