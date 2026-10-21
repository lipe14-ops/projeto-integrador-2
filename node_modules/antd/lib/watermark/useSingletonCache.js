"use strict";

var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _util = require("@rc-component/util");
var _is = require("../_util/is");
/**
 * Singleton cache will only take latest `cacheParams` as key
 * and return the result for callback matching.
 */
const useSingletonCache = () => {
  const cacheRef = React.useRef([null, null]);
  const getCache = (cacheKeys, callback) => {
    const filteredKeys = cacheKeys.map(item => (0, _is.isHTMLElement)(item) || Number.isNaN(item) ? '' : item);
    if (!(0, _util.isEqual)(cacheRef.current[0], filteredKeys)) {
      cacheRef.current = [filteredKeys, callback()];
    }
    return cacheRef.current[1];
  };
  return getCache;
};
var _default = exports.default = useSingletonCache;