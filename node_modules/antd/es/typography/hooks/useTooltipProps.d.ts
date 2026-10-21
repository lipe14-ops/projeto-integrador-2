import type { TooltipProps } from '../../tooltip';
declare const useTooltipProps: (tooltip: React.ReactNode | TooltipProps, editConfigText: React.ReactNode, children: React.ReactNode) => {
    title: string | number | bigint | boolean | import("react").ReactElement<unknown, string | import("react").JSXElementConstructor<any>> | Iterable<import("react").ReactNode> | Promise<string | number | bigint | boolean | import("react").ReactPortal | import("react").ReactElement<unknown, string | import("react").JSXElementConstructor<any>> | Iterable<import("react").ReactNode> | null | undefined> | import("../../_util/getRenderPropValue").RenderFunction | null | undefined;
    overlay?: React.ReactNode | import("../../_util/getRenderPropValue").RenderFunction;
    classNames?: ((info: {
        props: TooltipProps;
    }) => import("../../_util/hooks/useMergeSemantic/semanticType").DeepClassNameType<{
        root?: string;
        container?: string;
        arrow?: string;
    } | undefined>) | import("../../_util/hooks/useMergeSemantic/semanticType").DeepClassNameType<{
        root?: string;
        container?: string;
        arrow?: string;
    } | undefined>;
    styles?: ((info: {
        props: TooltipProps;
    }) => import("../../_util/hooks/useMergeSemantic/semanticType").DeepStylesType<{
        root?: React.CSSProperties;
        container?: React.CSSProperties;
        arrow?: React.CSSProperties;
    } | undefined>) | import("../../_util/hooks/useMergeSemantic/semanticType").DeepStylesType<{
        root?: React.CSSProperties;
        container?: React.CSSProperties;
        arrow?: React.CSSProperties;
    } | undefined>;
    style?: React.CSSProperties;
    className?: string;
    rootClassName?: string;
    color?: import("../../_util/type").LiteralUnion<import("../../_util/colors").PresetColorType>;
    placement?: import("../../tooltip").TooltipPlacement;
    builtinPlacements?: import("@rc-component/trigger").BuildInPlacements;
    openClassName?: string;
    arrow?: boolean | {
        pointAtCenter?: boolean;
    };
    autoAdjustOverflow?: boolean | import("../../tooltip").AdjustOverflow;
    getPopupContainer?: (triggerNode: HTMLElement) => HTMLElement;
    children?: React.ReactNode;
    destroyOnHidden?: boolean;
    destroyTooltipOnHide?: boolean | {
        keepParent?: boolean;
    };
    overlayStyle?: React.CSSProperties;
    overlayInnerStyle?: React.CSSProperties;
    overlayClassName?: string;
    motion?: {
        motionName?: string;
    };
    open?: boolean | undefined;
    defaultOpen?: boolean | undefined;
    onOpenChange?: (open: boolean) => void;
    afterOpenChange?: (open: boolean) => void;
    key?: import("react").Key | null | undefined;
    disabled?: boolean | undefined;
    id?: string | undefined;
    align?: import("@rc-component/trigger").AlignType | undefined;
    prefixCls?: string | undefined;
    zIndex?: number | undefined;
    onPopupAlign?: ((element: HTMLElement, align: import("@rc-component/trigger").AlignType) => void) | undefined;
    fresh?: boolean | undefined;
    mouseLeaveDelay?: number | undefined;
    mouseEnterDelay?: number | undefined;
    forceRender?: boolean | undefined;
    trigger?: (import("@rc-component/trigger").ActionType | import("@rc-component/trigger").ActionType[]) | undefined;
    getTooltipContainer?: ((node: HTMLElement) => HTMLElement) | undefined;
    unique?: boolean | undefined;
};
export default useTooltipProps;
