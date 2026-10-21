"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = useItemKey;
var _util = require("@rc-component/util");
function useItemKey(rowKey) {
  return (0, _util.useEvent)(item => typeof rowKey === 'function' ? rowKey(item) : item[rowKey]);
}