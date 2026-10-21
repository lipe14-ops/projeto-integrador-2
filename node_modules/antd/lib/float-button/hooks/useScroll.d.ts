type ScrollTarget = HTMLElement | Window | Document;
interface ScrollOptions {
    getTarget: () => ScrollTarget | null;
    showProgress: boolean;
    visibilityHeight: number;
}
declare const useScroll: (options: ScrollOptions) => {
    readonly scrollProgress: number;
    readonly visible: boolean;
};
export default useScroll;
