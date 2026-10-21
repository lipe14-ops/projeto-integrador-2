import type { ConfigProviderProps, Variant } from '../../config-provider';
type VariantComponents = keyof Pick<ConfigProviderProps, 'input' | 'inputPassword' | 'inputSearch' | 'otp' | 'inputNumber' | 'textArea' | 'mentions' | 'select' | 'cascader' | 'treeSelect' | 'datePicker' | 'timePicker' | 'rangePicker' | 'card'>;
/**
 * Compatible for legacy `bordered` prop.
 */
declare const useVariant: (component: VariantComponents, variant?: Variant, legacyBordered?: boolean, fallbackComponent?: VariantComponents) => [Variant, boolean, boolean];
export default useVariant;
