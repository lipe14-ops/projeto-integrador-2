import { isNonNullable } from '@rc-component/util';
const toList = (val, config = {}) => {
  if (!isNonNullable(val) && config?.skipEmpty) {
    return [];
  }
  return Array.isArray(val) ? val : [val];
};
export default toList;