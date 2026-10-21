"use strict";

var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = useDebounce;
var React = _interopRequireWildcard(require("react"));
var _util = require("@rc-component/util");
function useDebounce(value) {
  const [cacheValue, setCacheValue] = (0, _util.useDelayState)(value);
  React.useEffect(() => {
    setCacheValue(value, {
      ms: value.length ? 0 : 10
    });
  }, [value]);
  return cacheValue;
}