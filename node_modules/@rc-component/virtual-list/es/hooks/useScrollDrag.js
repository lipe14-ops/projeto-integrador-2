import { raf } from '@rc-component/util';
import * as React from 'react';
function smoothScrollOffset(offset) {
  return Math.floor(offset ** 0.5);
}
export function getPageXY(e, horizontal) {
  const obj = 'touches' in e ? e.touches[0] : e;
  return obj[horizontal ? 'pageX' : 'pageY'] - window[horizontal ? 'scrollX' : 'scrollY'];
}

/**
 * Check the element itself or any of its ancestors is draggable.
 * Use the IDL attribute instead of `[draggable]` selector so that
 * implicitly draggable elements (`a[href]`, `img`) are also covered.
 */
function isDraggable(ele) {
  let current = ele;
  while (current) {
    if (current.draggable) {
      return true;
    }
    current = current.parentElement;
  }
  return false;
}
export default function useScrollDrag(inVirtual, componentRef, onScrollOffset) {
  React.useEffect(() => {
    const ele = componentRef.current;
    if (inVirtual && ele) {
      let mouseDownLock = false;
      let rafId;
      let offset;
      const stopScroll = () => {
        raf.cancel(rafId);
      };
      const continueScroll = () => {
        stopScroll();
        rafId = raf(() => {
          onScrollOffset(offset);
          continueScroll();
        });
      };
      const clearDragState = () => {
        mouseDownLock = false;
        stopScroll();
      };
      const onMouseDown = e => {
        // Skip if element set draggable
        // Note the mousedown target is the deepest node in the event path (e.g. the
        // title span inside a Tree node), while `draggable` is set on the ancestor.
        if (isDraggable(e.target) || e.button !== 0) {
          return;
        }
        // Skip if nest List has handled this event
        const event = e;
        if (!event._virtualHandled) {
          event._virtualHandled = true;
          mouseDownLock = true;
        }
      };
      const onMouseMove = e => {
        if (mouseDownLock) {
          const mouseY = getPageXY(e, false);
          const {
            top,
            bottom
          } = ele.getBoundingClientRect();
          if (mouseY <= top) {
            const diff = top - mouseY;
            offset = -smoothScrollOffset(diff);
            continueScroll();
          } else if (mouseY >= bottom) {
            const diff = mouseY - bottom;
            offset = smoothScrollOffset(diff);
            continueScroll();
          } else {
            stopScroll();
          }
        }
      };
      ele.addEventListener('mousedown', onMouseDown);
      ele.ownerDocument.addEventListener('mouseup', clearDragState);
      ele.ownerDocument.addEventListener('mousemove', onMouseMove);
      ele.ownerDocument.addEventListener('dragend', clearDragState);
      return () => {
        ele.removeEventListener('mousedown', onMouseDown);
        ele.ownerDocument.removeEventListener('mouseup', clearDragState);
        ele.ownerDocument.removeEventListener('mousemove', onMouseMove);
        ele.ownerDocument.removeEventListener('dragend', clearDragState);
        stopScroll();
      };
    }
  }, [inVirtual]);
}