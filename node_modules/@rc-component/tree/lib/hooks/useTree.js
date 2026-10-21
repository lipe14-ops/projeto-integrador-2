"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = useTree;
var _util = require("@rc-component/util");
var React = _interopRequireWildcard(require("react"));
var _keyUtil = _interopRequireDefault(require("../utils/keyUtil"));
var _treeUtil = require("../utils/treeUtil");
function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
function _getRequireWildcardCache(e) { if ("function" != typeof WeakMap) return null; var r = new WeakMap(), t = new WeakMap(); return (_getRequireWildcardCache = function (e) { return e ? t : r; })(e); }
function _interopRequireWildcard(e, r) { if (!r && e && e.__esModule) return e; if (null === e || "object" != typeof e && "function" != typeof e) return { default: e }; var t = _getRequireWildcardCache(r); if (t && t.has(e)) return t.get(e); var n = { __proto__: null }, a = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var u in e) if ("default" !== u && Object.prototype.hasOwnProperty.call(e, u)) { var i = a ? Object.getOwnPropertyDescriptor(e, u) : null; i && (i.get || i.set) ? Object.defineProperty(n, u, i) : n[u] = e[u]; } return n.default = e, t && t.set(e, n), n; }
function useTree(treeData, config) {
  const {
    fieldNames
  } = config;
  const keyEntities = React.useMemo(() => {
    const {
      keyEntities
    } = (0, _treeUtil.convertDataToEntities)(treeData, {
      fieldNames
    });
    return keyEntities;
  }, [treeData, fieldNames]);
  const getPath = (0, _util.useEvent)(key => {
    const path = [];
    let entity = (0, _keyUtil.default)(keyEntities, key);
    while (entity) {
      path.unshift(entity);
      entity = entity.parent;
    }
    return path;
  });
  return {
    getPath
  };
}