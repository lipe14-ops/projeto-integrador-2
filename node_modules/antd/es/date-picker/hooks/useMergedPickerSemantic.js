import * as React from 'react';
import { clsx } from 'clsx';
import { useMergeSemantic, useSemanticRootStyle } from '../../_util/hooks/useMergeSemantic';
import { useComponentConfig } from '../../config-provider/context';
const useMergedPickerSemantic = (pickerType, classNames, styles, popupClassName, popupStyle, mergedProps, contextStyle) => {
  const {
    classNames: contextClassNames,
    style: componentContextStyle,
    styles: contextStyles
  } = useComponentConfig(pickerType);
  const mergedContextStyle = contextStyle === null ? undefined : contextStyle ?? componentContextStyle;
  const contextStyleRoot = useSemanticRootStyle(mergedContextStyle);
  const [mergedClassNames, mergedStyles] = useMergeSemantic([contextClassNames, classNames], [contextStyles, contextStyleRoot, styles], {
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
        root: clsx(mergedClassNames.popup?.root, popupClassName)
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
export default useMergedPickerSemantic;