import React from 'react';
import type { ListyClassNames, ListyRef, ListyScrollToConfig, ListyStyles, ListyProps as RcListyProps, ScrollAlign } from '@rc-component/listy';
import type { GenerateSemantic } from '../_util/hooks/useMergeSemantic/semanticType';
import type { AnyObject } from '../_util/type';
export type ListySemanticType = {
    classNames?: ListyClassNames;
    styles?: ListyStyles;
};
export type ListySemanticAllType = GenerateSemantic<ListySemanticType, ListyProps>;
export interface ListyProps<T = AnyObject, K extends React.Key = React.Key> extends Omit<RcListyProps<T, K>, 'itemHeight' | 'direction' | 'classNames' | 'styles'> {
    rootClassName?: string;
    className?: string;
    style?: React.CSSProperties;
    classNames?: ListySemanticAllType['classNamesAndFn'];
    styles?: ListySemanticAllType['stylesAndFn'];
}
type ListyComponent = (<T = AnyObject, K extends React.Key = React.Key>(props: ListyProps<T, K> & {
    ref?: React.Ref<ListyRef>;
}) => React.ReactElement) & {
    displayName?: string;
};
declare const Listy: ListyComponent;
export type { ListyClassNames, ListyRef, ListyScrollToConfig, ListyStyles, ScrollAlign };
export default Listy;
