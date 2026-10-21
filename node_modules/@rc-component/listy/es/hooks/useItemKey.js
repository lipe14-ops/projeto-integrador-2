import { useEvent } from '@rc-component/util';
export default function useItemKey(rowKey) {
  return useEvent(item => typeof rowKey === 'function' ? rowKey(item) : item[rowKey]);
}