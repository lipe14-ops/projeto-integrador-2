import type { GetDefaultToken } from '../../theme/internal';
export interface ComponentToken {
    /**
     * @nameZH 列表项纵向内间距
     * @nameEN Item Vertical Padding
     * @desc 列表项的纵向内间距。
     * @descEN Vertical padding of a list item.
     */
    itemPaddingBlock: number;
    /**
     * @nameZH 列表项横向内间距
     * @nameEN Item Horizontal Padding
     * @desc 列表项的横向内间距。
     * @descEN Horizontal padding of a list item.
     */
    itemPaddingInline: number;
}
export declare const prepareComponentToken: GetDefaultToken<'Listy'>;
declare const _default: (prefixCls: string, rootCls?: string) => readonly [string, string];
export default _default;
