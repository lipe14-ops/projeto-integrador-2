import React from 'react';
import type { QRCodeProps, QRProps, QRPropsCanvas, QRPropsSvg } from './interface';
export type { QRCodeProps, QRProps, QRPropsCanvas, QRPropsSvg };
export interface QRCodeRef {
    nativeElement: HTMLDivElement;
}
declare const QRCode: React.ForwardRefExoticComponent<QRCodeProps & React.RefAttributes<QRCodeRef>>;
export default QRCode;
