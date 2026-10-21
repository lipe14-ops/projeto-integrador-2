import { useEvent } from '@rc-component/util';
import * as React from 'react';
import getEntity from "../utils/keyUtil";
import { convertDataToEntities } from "../utils/treeUtil";
export default function useTree(treeData, config) {
  const {
    fieldNames
  } = config;
  const keyEntities = React.useMemo(() => {
    const {
      keyEntities
    } = convertDataToEntities(treeData, {
      fieldNames
    });
    return keyEntities;
  }, [treeData, fieldNames]);
  const getPath = useEvent(key => {
    const path = [];
    let entity = getEntity(keyEntities, key);
    while (entity) {
      path.unshift(entity);
      entity = entity.parent;
    }
    return path;
  });
  return {
    getPath
  };
}