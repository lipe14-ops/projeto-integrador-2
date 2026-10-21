export type GetCache<T, R> = (cacheKeys: T, callback: () => R) => R;
/**
 * Singleton cache will only take latest `cacheParams` as key
 * and return the result for callback matching.
 */
declare const useSingletonCache: <T extends any[], R>() => GetCache<T, R>;
export default useSingletonCache;
