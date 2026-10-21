"use strict";

var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _configProvider = require("../../config-provider");
var _context = require("../context");
/**
 * Compatible for legacy `bordered` prop.
 */
const useVariant = (component, variant, legacyBordered, fallbackComponent) => {
  const config = React.useContext(_configProvider.ConfigContext);
  const {
    variant: configVariant,
    [component]: componentConfig
  } = config;
  const ctxVariant = React.useContext(_context.VariantContext);
  const fallbackComponentConfig = fallbackComponent ? config[fallbackComponent] : undefined;
  const configComponentVariant = componentConfig?.variant ?? fallbackComponentConfig?.variant;
  const isVariantConfigured = typeof variant !== 'undefined' || legacyBordered === false || typeof ctxVariant !== 'undefined' || typeof configComponentVariant !== 'undefined' || typeof configVariant !== 'undefined';
  let mergedVariant;
  if (typeof variant !== 'undefined') {
    mergedVariant = variant;
  } else if (legacyBordered === false) {
    mergedVariant = 'borderless';
  } else {
    // form variant > component global variant > fallback component global variant > global variant
    mergedVariant = ctxVariant ?? configComponentVariant ?? configVariant ?? 'outlined';
  }
  const enableVariantCls = _configProvider.Variants.includes(mergedVariant);
  return [mergedVariant, enableVariantCls, isVariantConfigured];
};
var _default = exports.default = useVariant;