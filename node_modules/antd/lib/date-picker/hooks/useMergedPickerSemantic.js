"use strict";

var _interopRequireWildcard = require("@babel/runtime/helpers/interopRequireWildcard").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var React = _interopRequireWildcard(require("react"));
var _clsx = require("clsx");
var _useMergeSemantic = require("../../_util/hooks/useMergeSemantic");
var _context = require("../../config-provider/context");
const useMergedPickerSemantic = (pickerType, classNames, styles, popupClassName, popupStyle, mergedProps, contextStyle) => {
  const {
    classNames: contextClassNames,
    style: componentContextStyle,
    styles: contextStyles
  } = (0, _context.useComponentConfig)(pickerType);
  const mergedContextStyle = contextStyle === null ? undefined : contextStyle ?? componentContextStyle;
  const contextStyleRoot = (0, _useMergeSemantic.useSemanticRootStyle)(mergedContextStyle);
  const [mergedClassNames, mergedStyles] = (0, _useMergeSemantic.useMergeSemantic)([contextClassNames, classNames], [contextStyles, contextStyleRoot, styles], {
    props: mergedProps
  }, {
    popup: {
      _default: 'root'
    }
  });
  return React.useMemo(() => {
    // ClassNames
    const filledClassNames = {
      ...mergedClassNames,
      popup: {
        ...mergedClassNames.popup,
        root: (0, _clsx.clsx)(mergedClassNames.popup?.root, popupClassName)
      }
    };
    // Styles
    const filledStyles = {
      ...mergedStyles,
      popup: {
        ...mergedStyles.popup,
        root: {
          ...mergedStyles.popup?.root,
          ...popupStyle
        }
      }
    };
    // Return
    return [filledClassNames, filledStyles];
  }, [mergedClassNames, mergedStyles, popupClassName, popupStyle]);
};
var _default = exports.default = useMergedPickerSemantic;