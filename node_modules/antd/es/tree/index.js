"use client";

import { TreeNode, useTree } from '@rc-component/tree';
import DirectoryTree from './DirectoryTree';
import TreePure from './Tree';
const Tree = TreePure;
Tree.DirectoryTree = DirectoryTree;
Tree.TreeNode = TreeNode;
Tree.useTree = useTree;
export default Tree;