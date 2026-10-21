"use strict";

var _interopRequireDefault = require("@babel/runtime/helpers/interopRequireDefault").default;
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
var _util = require("@rc-component/util");
var _easings = require("./easings");
var _getScroll = _interopRequireDefault(require("./getScroll"));
var _is = require("./is");
const scrollTo = (y, options = {}) => {
  const {
    getContainer = () => window,
    callback,
    duration = 450
  } = options;
  const container = getContainer();
  const scrollTop = (0, _getScroll.default)(container);
  const scroll = top => {
    if ((0, _is.isWindow)(container)) {
      container.scrollTo(window.pageXOffset, top);
    } else if ((0, _is.isDocument)(container)) {
      container.documentElement.scrollTop = top;
    } else {
      container.scrollTop = top;
    }
  };
  if (duration <= 0) {
    scroll(y);
    if ((0, _is.isFunction)(callback)) {
      callback();
    }
    return () => {};
  }
  const startTime = Date.now();
  let rafId;
  const frameFunc = () => {
    const timestamp = Date.now();
    const time = timestamp - startTime;
    const nextScrollTop = (0, _easings.easeInOutCubic)(time > duration ? duration : time, scrollTop, y, duration);
    scroll(nextScrollTop);
    if (time < duration) {
      rafId = (0, _util.raf)(frameFunc);
    } else if ((0, _is.isFunction)(callback)) {
      callback();
    }
  };
  rafId = (0, _util.raf)(frameFunc);
  return () => {
    _util.raf.cancel(rafId);
  };
};
var _default = exports.default = scrollTo;