package bench;
/** Injected observation/failure seam: production default is no-op. */
public interface OperationProbe {
    default void locked(int batch) throws BusinessFailure {}
    default void afterOrder(int order) throws BusinessFailure {}
    default void beforeRelease(int sku) throws BusinessFailure {}
}
