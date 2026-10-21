import * as React from 'react';
export interface CardGridProps extends React.HTMLAttributes<HTMLDivElement> {
    prefixCls?: string;
    className?: string;
    hoverable?: boolean;
    style?: React.CSSProperties;
}
export interface CardGridRef {
    nativeElement: HTMLDivElement;
}
declare const CardGrid: React.ForwardRefExoticComponent<CardGridProps & React.RefAttributes<CardGridRef>>;
export default CardGrid;
