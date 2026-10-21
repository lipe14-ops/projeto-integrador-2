import InternalCard from './Card';
import CardGrid from './CardGrid';
import CardMeta from './CardMeta';
export type { CardProps, CardTabListType } from './Card';
export type { CardGridProps } from './CardGrid';
export type { CardGridRef } from './CardGrid';
export type { CardMetaProps } from './CardMeta';
export type { CardMetaRef } from './CardMeta';
type InternalCardType = typeof InternalCard;
export interface CardInterface extends InternalCardType {
    Grid: typeof CardGrid;
    Meta: typeof CardMeta;
}
declare const Card: CardInterface;
export default Card;
