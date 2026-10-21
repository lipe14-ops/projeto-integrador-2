import type { useBaseProps } from '@rc-component/select';
import * as React from 'react';
export interface RefOptionListProps {
    onKeyDown: React.KeyboardEventHandler;
    onKeyUp: React.KeyboardEventHandler;
}
export type RawOptionListProps = Pick<ReturnType<typeof useBaseProps>, 'prefixCls' | 'multiple' | 'searchValue' | 'toggleOpen' | 'notFoundContent' | 'direction' | 'open' | 'disabled'> & {
    lockOptions?: boolean;
};
declare const RawOptionList: React.ForwardRefExoticComponent<Pick<import("@rc-component/select/es/hooks/useBaseProps").BaseSelectContextProps, "disabled" | "prefixCls" | "searchValue" | "direction" | "notFoundContent" | "open" | "multiple" | "toggleOpen"> & {
    lockOptions?: boolean | undefined;
} & React.RefAttributes<RefOptionListProps>>;
export default RawOptionList;
