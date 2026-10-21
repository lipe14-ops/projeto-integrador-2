"use client";

import * as React from 'react';
import SearchOutlined from "@ant-design/icons/es/icons/SearchOutlined";
import Input from '../input/Input';
const Search = props => {
  const {
    placeholder = '',
    value,
    prefixCls,
    disabled,
    onChange,
    handleClear
  } = props;
  const handleChange = React.useCallback(e => {
    if (e.type === 'click') {
      handleClear?.();
    } else {
      onChange?.(e);
    }
  }, [onChange, handleClear]);
  return /*#__PURE__*/React.createElement(Input, {
    placeholder: placeholder,
    className: prefixCls,
    value: value,
    onChange: handleChange,
    disabled: disabled,
    allowClear: true,
    prefix: /*#__PURE__*/React.createElement(SearchOutlined, null)
  });
};
if (process.env.NODE_ENV !== 'production') {
  Search.displayName = 'Search';
}
export default Search;