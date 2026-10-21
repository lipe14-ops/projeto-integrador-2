import React from 'react';
import type { PropsWithChildren } from 'react';
import type { GenerateSemantic } from '../_util/hooks/useMergeSemantic/semanticType';
import type { AvatarProps } from './Avatar';
import SkeletonAvatar from './Avatar';
import SkeletonButton from './Button';
import SkeletonImage from './Image';
import SkeletonInput from './Input';
import SkeletonNode from './Node';
import type { SkeletonParagraphProps } from './Paragraph';
import type { SkeletonTitleProps } from './Title';
type SkeletonAvatarProps = Omit<AvatarProps, 'active'>;
export type SkeletonSemanticType = {
    classNames?: {
        root?: string;
        header?: string;
        section?: string;
        avatar?: string;
        title?: string;
        paragraph?: string;
    };
    styles?: {
        root?: React.CSSProperties;
        header?: React.CSSProperties;
        section?: React.CSSProperties;
        avatar?: React.CSSProperties;
        title?: React.CSSProperties;
        paragraph?: React.CSSProperties;
    };
};
export type SkeletonSemanticAllType = GenerateSemantic<SkeletonSemanticType, SkeletonProps>;
export interface SkeletonProps {
    active?: boolean;
    loading?: boolean;
    prefixCls?: string;
    className?: string;
    rootClassName?: string;
    style?: React.CSSProperties;
    avatar?: SkeletonAvatarProps | boolean;
    title?: SkeletonTitleProps | boolean;
    paragraph?: SkeletonParagraphProps | boolean;
    round?: boolean;
    classNames?: SkeletonSemanticAllType['classNamesAndFn'];
    styles?: SkeletonSemanticAllType['stylesAndFn'];
}
export interface SkeletonRef {
    nativeElement: HTMLDivElement | null;
}
type CompoundedComponent = React.ForwardRefExoticComponent<PropsWithChildren<SkeletonProps> & React.RefAttributes<SkeletonRef>> & {
    Button: typeof SkeletonButton;
    Avatar: typeof SkeletonAvatar;
    Input: typeof SkeletonInput;
    Image: typeof SkeletonImage;
    Node: typeof SkeletonNode;
};
declare const Skeleton: CompoundedComponent;
export default Skeleton;
