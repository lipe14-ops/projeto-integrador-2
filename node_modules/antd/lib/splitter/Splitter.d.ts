import React from 'react';
import type { SplitterProps } from './interface';
export interface SplitterRef {
    nativeElement: HTMLDivElement;
}
declare const Splitter: React.ForwardRefExoticComponent<SplitterProps & {
    children?: React.ReactNode | undefined;
} & React.RefAttributes<SplitterRef>>;
export default Splitter;
