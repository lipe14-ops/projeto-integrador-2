"use client";

import _toConsumableArray from "@babel/runtime/helpers/esm/toConsumableArray";
import * as React from 'react';
import { isNonNullable, omit, useControlledState } from '@rc-component/util';
import { clsx } from 'clsx';
import { isNumber, isString } from '../_util/is';
import { ConfigContext } from '../config-provider';
import useCSSVarCls from '../config-provider/hooks/useCSSVarCls';
import Checkbox from './Checkbox';
import GroupContext from './GroupContext';
import useStyle from './style';
const CheckboxGroup = /*#__PURE__*/React.forwardRef((props, ref) => {
  const {
    defaultValue,
    children,
    options = [],
    prefixCls: customizePrefixCls,
    className,
    rootClassName,
    style,
    onChange,
    role = 'group',
    ...restProps
  } = props;
  const {
    getPrefixCls,
    direction
  } = React.useContext(ConfigContext);
  const [value, setValue] = useControlledState(defaultValue || [], restProps.value);
  const mergedValue = value || [];
  const [registeredValues, setRegisteredValues] = React.useState([]);
  const memoizedOptions = React.useMemo(() => {
    return options.map(option => {
      if (isString(option) || isNumber(option)) {
        return {
          label: option,
          value: option
        };
      }
      return option;
    }).filter(item => isNonNullable(item) && isNonNullable(item.value));
  }, [options]);
  const cancelValue = val => {
    setRegisteredValues(prevValues => prevValues.filter(v => v !== val));
  };
  const registerValue = val => {
    setRegisteredValues(prevValues => [].concat(_toConsumableArray(prevValues), [val]));
  };
  const toggleOption = option => {
    const optionIndex = mergedValue.indexOf(option.value);
    const newValue = _toConsumableArray(mergedValue);
    if (optionIndex === -1) {
      newValue.push(option.value);
    } else {
      newValue.splice(optionIndex, 1);
    }
    setValue(newValue);
    onChange?.(newValue.filter(val => registeredValues.includes(val)).sort((a, b) => {
      const indexA = memoizedOptions.findIndex(opt => opt.value === a);
      const indexB = memoizedOptions.findIndex(opt => opt.value === b);
      return indexA - indexB;
    }));
  };
  const prefixCls = getPrefixCls('checkbox', customizePrefixCls);
  const groupPrefixCls = `${prefixCls}-group`;
  const rootCls = useCSSVarCls(prefixCls);
  const [hashId, cssVarCls] = useStyle(prefixCls, rootCls);
  const domProps = omit(restProps, ['value', 'disabled']);
  const childrenNode = Array.isArray(memoizedOptions) && memoizedOptions.length > 0 ? memoizedOptions.map(option => (/*#__PURE__*/React.createElement(Checkbox, {
    prefixCls: prefixCls,
    key: option.value.toString(),
    disabled: 'disabled' in option ? option.disabled : restProps.disabled,
    value: option.value,
    checked: mergedValue.includes(option.value),
    onChange: option.onChange,
    className: clsx(`${groupPrefixCls}-item`, option.className),
    style: option.style,
    title: option.title,
    id: option.id,
    required: option.required
  }, option.label))) : children;
  const memoizedContext = React.useMemo(() => ({
    toggleOption,
    value: mergedValue,
    disabled: restProps.disabled,
    name: restProps.name,
    // https://github.com/ant-design/ant-design/issues/16376
    registerValue,
    cancelValue
  }), [toggleOption, mergedValue, restProps.disabled, restProps.name, registerValue, cancelValue]);
  const classString = clsx(groupPrefixCls, {
    [`${groupPrefixCls}-rtl`]: direction === 'rtl'
  }, className, rootClassName, cssVarCls, rootCls, hashId);
  return /*#__PURE__*/React.createElement("div", {
    className: classString,
    style: style,
    role: role,
    ...domProps,
    ref: ref
  }, /*#__PURE__*/React.createElement(GroupContext.Provider, {
    value: memoizedContext
  }, childrenNode));
});
export { GroupContext };
export default CheckboxGroup;