import type { DisplayValueType, Mode } from '../interface';
import type React from 'react';
export interface AllowClearConfig {
    allowClear: boolean;
    clearIcon: React.ReactNode;
    label: string;
}
export declare const useAllowClear: (prefixCls: string, displayValues: DisplayValueType[], allowClear?: boolean | {
    clearIcon?: React.ReactNode;
    label?: string;
}, clearIcon?: React.ReactNode, disabled?: boolean, mergedSearchValue?: string, mode?: Mode) => AllowClearConfig;
