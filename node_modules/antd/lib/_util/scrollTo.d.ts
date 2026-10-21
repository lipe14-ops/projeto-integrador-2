interface ScrollToOptions {
    /** Scroll container, default as window */
    getContainer?: () => HTMLElement | Window | Document;
    /** Scroll end callback */
    callback?: () => void;
    /** Animation duration, default as 450 */
    duration?: number;
}
declare const scrollTo: (y: number, options?: ScrollToOptions) => () => void;
export default scrollTo;
