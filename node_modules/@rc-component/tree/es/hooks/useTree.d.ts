import type { BasicDataNode, DataEntity, DataNode, FieldNames, Key } from '../interface';
export interface UseTreeConfig {
    fieldNames?: FieldNames;
}
export interface TreeInstance<TreeDataType extends DataNode | BasicDataNode = DataNode> {
    getPath: (key: Key) => DataEntity<TreeDataType>[];
}
export default function useTree<TreeDataType extends DataNode | BasicDataNode = DataNode>(treeData: TreeDataType[], config: UseTreeConfig): TreeInstance<TreeDataType>;
