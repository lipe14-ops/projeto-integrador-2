import * as React from 'react';
import { isEqual } from '@rc-component/util';
import { isHTMLElement } from '../_util/is';
/**
 * Singleton cache will only take latest `cacheParams` as key
 * and return the result for callback matching.
 */
const useSingletonCache = () => {
  const cacheRef = React.useRef([null, null]);
  const getCache = (cacheKeys, callback) => {
    const filteredKeys = cacheKeys.map(item => isHTMLElement(item) || Number.isNaN(item) ? '' : item);
    if (!isEqual(cacheRef.current[0], filteredKeys)) {
      cacheRef.current = [filteredKeys, callback()];
    }
    return cacheRef.current[1];
  };
  return getCache;
};
export default useSingletonCache;