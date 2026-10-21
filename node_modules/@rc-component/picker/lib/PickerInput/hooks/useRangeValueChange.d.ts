/** Change source of a field. / Field 的变更来源。 */
export type RangeValueChangeSource = 'input' | 'remove' | 'keyboard-submit' | 'keyboard-submit-weak' | 'esc' | 'panel-intermediate' | 'panel-final' | 'popupClose' | 'field-switch' | 'confirm';
/** Resolved operation for one field interaction. / 一次 field 交互最终执行的操作。 */
export type RangeValueChangeAction = 'modify' | 'submitCurrent' | 'switchNext' | 'finish' | 'abort' | 'resetCurrent' | 'resetCurrentAndSwitchNext' | 'resetAll';
/** Receive a field interaction and its optional value. / 接收 field 交互及可选变更值。 */
export type TriggerChange<FieldValue> = (index: number, source: RangeValueChangeSource, value?: FieldValue) => void;
/** Read the latest temporary CalendarValue. / 读取最新的临时 CalendarValue。 */
export type GetCalendarValue<FieldValue> = () => readonly (FieldValue | null | undefined)[];
/** Update one field in CalendarValue. / 更新 CalendarValue 中的一个 field。 */
export type TriggerCalendarChange<FieldValue> = (index: number, value: FieldValue) => void;
/**
 * Flush one field and optionally emit the final change.
 * 提交一个 field，并按需触发最终 change。
 */
export type FlushSubmit = (index: number, needTriggerChange: boolean) => void;
/**
 * Reset one field, or all fields when index is omitted.
 * 重置指定 field；未传 index 时重置全部 field。
 */
export type ResetValue = (index?: number) => void;
export type UseRangeValueChangeReturn<FieldValue> = [
    currentIndex: number | null,
    activeIndex: number,
    forceFocus: boolean,
    triggeredFields: number[],
    triggerChange: TriggerChange<FieldValue>,
    reset: VoidFunction
];
/**
 * Coordinate CalendarValue updates, part submits and final submits for any
 * number of fields.
 * 统一管理任意数量 field 的 CalendarValue 更新、局部提交与最终提交。
 *
 * Flow / 流程：
 * Every event is first resolved from `source`, `needConfirm`, `allowEmpty` and
 * the field indexes to one action. State changes only happen while executing
 * that action, so event sources never submit or reset values on their own.
 * 每个事件先根据 `source`、`needConfirm`、`allowEmpty` 与 field index 得到唯一
 * action。状态只在执行 action 时改变，事件来源本身不直接提交或重置值。
 *
 * Index transitions also expose whether focus must follow the next field.
 * Confirm-like operations and a popup close following a panel operation
 * switch focus strongly. A popup close following input, Tab and an actual
 * field focus switch only update the expected index.
 * index 切换还会同步给出是否必须跟随聚焦下一个 field。确认类操作，以及面板
 * 操作后的 popup 关闭使用强切换；input 后的 popup 关闭、Tab 与真实 field
 * 聚焦切换只更新预期 index。
 *
 * Source resolution / 事件解析：
 *
 * - `esc` always resolves to `resetAll`.
 *   `esc` 始终解析为 `resetAll`。
 * - With no current field, `popupClose` resolves to `resetAll`; any other
 *   non-cancel event starts a new interaction from its field.
 *   没有当前 field 时，`popupClose` 解析为 `resetAll`；其余非撤销事件从
 *   对应 field 开始新一轮交互。
 * - `field-switch` advances exactly one field in circular order. `needConfirm`
 *   locks an unconfirmed non-empty field unless it allows empty; an allow-empty
 *   field is reset before advancing.
 *   `field-switch` 只允许按循环顺序推进一个 field。`needConfirm` 会锁定未确认
 *   且非空的 field；允许空值时先重置再推进。
 * - Other sources must target the current field. `input` and
 *   `panel-intermediate` modify it; `remove` explicitly submits the removed
 *   value even when the field does not allow empty. `panel-final` advances only
 *   without confirmation; `keyboard-submit-weak` part-submits without
 *   advancing; `keyboard-submit` and `confirm` advance only when the field has
 *   a value or allows empty.
 *   其余来源必须指向当前 field。`input` 与 `panel-intermediate` 只修改；
 *   `remove` 会明确提交删除后的值，即使 field 不允许为空；`panel-final`
 *   仅在无需确认时推进；`keyboard-submit-weak` 只做局部提交而不推进；
 *   `keyboard-submit` 与 `confirm` 仅在有值或允许空值时推进。
 * - `popupClose` finishes an untouched interaction. Without confirmation it
 *   submits a valid field; with confirmation it submits only after every field
 *   has participated, otherwise it resets all temporary values. A modified
 *   allow-empty field is reset before the final submit.
 *   `popupClose` 会直接结束未修改的交互。无需确认时提交有效 field；需要确认时
 *   仅在所有 field 都参与过后提交，否则重置全部临时值。当前 field 已修改且
 *   允许为空时，会先重置当前值再完成提交。
 *
 * Action execution / Action 执行：
 *
 * - `modify`: update or record the current CalendarValue.
 *   更新或记录当前 CalendarValue。
 * - `submitCurrent`: part-submit the current field without advancing.
 *   局部提交当前 field，但不推进。
 * - `switchNext`: submit the current field and advance to the next field.
 *   提交当前 field 并推进到下一个 field。
 * - `finish`: end an interaction in which no field was modified without
 *   resetting values. / 结束所有 field 均未修改的交互，不重置任何值。
 * - `abort`: stop without changing any state.
 *   直接短路，不改变任何状态。
 * - `resetCurrent`: discard only the current field.
 *   仅撤销当前 field。
 * - `resetCurrentAndSwitchNext`: discard the current temporary value and
 *   advance without submitting. Revisiting a field starts a new round.
 *   撤销当前临时值并直接推进，不触发提交；再次进入已访问 field 时开启新一轮。
 * - `resetAll`: discard all temporary values and end the interaction.
 *   撤销全部临时值并结束本轮交互。
 */
export default function useRangeValueChange<FieldValue = unknown>(fieldCount: number, needConfirm: boolean, allowEmpty: readonly boolean[], getCalendarValue: GetCalendarValue<FieldValue>, triggerCalendarChange: TriggerCalendarChange<FieldValue>, flushSubmit: FlushSubmit, resetValue: ResetValue): UseRangeValueChangeReturn<FieldValue>;
