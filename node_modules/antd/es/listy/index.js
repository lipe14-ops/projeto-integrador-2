"use client";

import React from 'react';
import RcListy from '@rc-component/listy';
import { clsx } from 'clsx';
import { useMergeSemantic, useSemanticRootStyle } from '../_util/hooks/useMergeSemantic';
import { ConfigContext, useComponentConfig } from '../config-provider/context';
import useCSSVarCls from '../config-provider/hooks/useCSSVarCls';
import { useToken } from '../theme/internal';
import useStyle from './style';
const InternalListy = (props, ref) => {
  const {
    prefixCls: customizePrefixCls,
    rootClassName,
    className,
    style,
    classNames,
    styles,
    virtual,
    ...restProps
  } = props;
  const {
    getPrefixCls,
    direction,
    className: contextClassName,
    style: contextStyle,
    classNames: contextClassNames,
    styles: contextStyles
  } = useComponentConfig('listy');
  const {
    virtual: contextVirtual
  } = React.useContext(ConfigContext);
  const prefixCls = getPrefixCls('listy', customizePrefixCls);
  const rootCls = useCSSVarCls(prefixCls);
  const [hashId, cssVarCls] = useStyle(prefixCls, rootCls);
  const [, token] = useToken();
  const listyToken = {
    ...token,
    ...token.Listy
  };
  const itemHeight = listyToken.fontHeight + (listyToken.itemPaddingBlock ?? listyToken.paddingSM) * 2;
  const contextStyleRoot = useSemanticRootStyle(contextStyle);
  const styleRoot = useSemanticRootStyle(style);
  const [mergedClassNames, mergedStyles] = useMergeSemantic([contextClassNames, classNames], [contextStyles, contextStyleRoot, styles, styleRoot], {
    props: props
  });
  const rootClassNames = clsx(contextClassName, mergedClassNames.root, rootClassName, className, hashId, cssVarCls, rootCls);
  const mergedVirtual = virtual ?? contextVirtual ?? false;
  return /*#__PURE__*/React.createElement(RcListy, {
    ...restProps,
    ref: ref,
    prefixCls: prefixCls,
    direction: direction,
    virtual: mergedVirtual,
    itemHeight: itemHeight,
    classNames: {
      ...mergedClassNames,
      root: rootClassNames
    },
    styles: mergedStyles
  });
};
const Listy = /*#__PURE__*/React.forwardRef(InternalListy);
if (process.env.NODE_ENV !== 'production') {
  Listy.displayName = 'Listy';
}
export default Listy;