# encoding: utf-8
from __future__ import division, print_function, unicode_literals

import objc
from GlyphsApp import Glyphs, MOUSEDOWN, MOUSEUP, MOUSEMOVED

from GlyphsApp.plugins import ReporterPlugin
from AppKit import (
    NSBezierPath,
    NSClassFromString,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSPoint,
    NSRect,
    NSString,
)


plugin_id = "com.lucasfonts.MoveableSidebearings"
DEBUG = False
SNAP_TOLERANCE = 5


class MetricsHandles(ReporterPlugin):
    @objc.python_method
    def settings(self):
        self.menuName = "Moveable Sidebearings"

    @objc.python_method
    def start(self):
        self.active_metric = None
        self.drag_start = None
        self.dragging = False
        self.mouse_position = (0, 0)
        self.willActivate()

    @objc.python_method
    def willActivate(self):
        Glyphs.addCallback(self.mouseDidMove, MOUSEMOVED)
        Glyphs.addCallback(self.mouseDown_, MOUSEDOWN)
        Glyphs.addCallback(self.mouseUp_, MOUSEUP)

    @objc.python_method
    def willDeactivate(self):
        Glyphs.removeCallback(self.mouseDidMove, MOUSEMOVED)
        Glyphs.removeCallback(self.mouseDown_, MOUSEDOWN)
        Glyphs.removeCallback(self.mouseUp_, MOUSEUP)

    @objc.python_method
    def foreground(self, layer):
        # Get the mouse position
        try:
            self.mouse_position = (
                self.controller.graphicView().getActiveLocation_(
                    Glyphs.currentEvent()
                )
            )
        except Exception as e:
            self.logToConsole("foreground: mouse_position: %s" % str(e))
            self.mouse_position = (0, 0)

        x, y = self.mouse_position

        if self.dragging:
            metricsLocked = self.metricsAreLocked(layer)
            if self.metricsAreLocked(layer):
                side = self.active_metric[0]
                if side == "LSB":
                    x = 0.5
                elif side == "RSB":
                    x = layer.width - 0.5

            dist = self.getDraggedDistance()
            # Live update the change
            # if not metricsLocked:
            #     self.setMetrics(self.active_metric, dist)

            # Draw the dragging handle

            self._drawHandle(
                handle_x=(x, 1),
                width=1 / self.getScale(),
                metric=(self.active_metric[0], dist, layer),
                alpha=1.0,
                locked=metricsLocked,
            )
            return

        # Is the mouse inside the "hot spot"?
        # If yes, display drag handles

        try:
            master = layer.master
        except KeyError:
            return

        if y < master.descender or y > master.ascender:
            self.active_metric = None
            return

        if x < 0 or x > layer.width:
            # Mouse is outside the glyph
            self.active_metric = None
            return

        snap_tolerance = SNAP_TOLERANCE / self.getScale()

        if x > snap_tolerance and x < layer.width - snap_tolerance:
            # Mouse is too far inside the glyph
            self.active_metric = None
            return

        currentController = self.controller.view().window().windowController()
        if currentController:
            tool = currentController.toolDrawDelegate()
            # don't activate if on cursor tool, or pan tool
            if not (
                # tool.isKindOfClass_(NSClassFromString("GlyphsToolText")) or
                tool.isKindOfClass_(NSClassFromString("GlyphsToolHand"))
                or tool.isKindOfClass_(
                    NSClassFromString("GlyphsToolTrueTypeInstructor")
                )
            ):
                if x < snap_tolerance:
                    handle_x = (0, snap_tolerance)
                    metric = ("LSB", layer.LSB, layer)
                else:
                    handle_x = (layer.width - snap_tolerance, snap_tolerance)
                    metric = ("RSB", layer.RSB, layer)
                self.active_metric = metric
                self._drawHandle(handle_x, snap_tolerance, metric)
        else:
            self.active_metric = None

    @objc.python_method
    def _drawHandle(self, handle_x, width, metric, alpha=0.3, locked=False):
        pos, _ = handle_x
        master = metric[2].master
        NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.9, 0.1, 0.0, alpha
        ).set()
        rect = NSRect(
            origin=(pos, master.descender),
            size=(width, master.ascender - master.descender),
        )
        NSBezierPath.bezierPathWithRect_(rect).fill()
        self._drawTextLabel(handle_x, width, metric, alpha, locked)

    @objc.python_method
    def _drawTextLabel(self, handle_x, width, metric, alpha=0.3, locked=False):
        scale = self.getScale()
        text_size = 11 / scale
        text_dist = 5 / scale
        metric_name, value, layer = metric
        if locked:
            shown_value = "🔒︎"
        elif metric_name == "LSB" and self.dragging:
            shown_value = "∆%g = %g" % (value, layer.LSB - value)
        elif metric_name == "RSB" and self.dragging:
            shown_value = "∆%g = %g" % (value, layer.RSB + value)
        else:
            shown_value = "%g" % value

        attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(text_size),
            NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.9, 0.1, 0.0, alpha
            ),
        }
        myString = NSString.string().stringByAppendingString_(shown_value)
        bbox = myString.sizeWithAttributes_(attrs)
        bw = bbox.width
        bh = bbox.height

        text_pt = NSPoint()
        text_pt.y = self.mouse_position[1]
        if metric_name == "LSB":
            if self.dragging:
                text_pt.x = handle_x[0] + text_dist
            else:
                text_pt.x = width + text_dist
        elif metric_name == "RSB":
            if self.dragging:
                text_pt.x = handle_x[0] - text_dist - bw
            else:
                text_pt.x = layer.width - width - text_dist - bw
        else:
            text_pt.x = self.mouse_position[0] - text_dist - bw

        rr = NSRect(origin=(text_pt.x, text_pt.y), size=(bw, bh))
        myString.drawInRect_withAttributes_(rr, attrs)

    @objc.python_method
    def getDraggedDistance(self):
        if self.drag_start is None:
            return 0

        return int(round(self.mouse_position[0] - self.drag_start))

    @objc.python_method
    def metricsAreLocked(self, layer):
        cp1 = "Link Metrics With First Master"
        cp2 = "Link Metrics With Master"
        if (
            cp1 in layer.master.customParameters
            and layer.master.customParameters[cp1] == 1
            or cp2 in layer.master.customParameters
            and layer.master.customParameters[cp2] == 1
        ):
            return True
        return False

    @objc.python_method
    def setMetrics(self, metrics, delta):
        if delta == 0:
            return

        side, _, layer = metrics

        if self.metricsAreLocked(layer):
            return

        layer.parent.beginUndo()
        if side == "LSB":
            layer.LSB -= delta
        elif side == "RSB":
            layer.width += delta
        else:
            layer.LSB += delta
            layer.width -= delta
        layer.parent.endUndo()

    @objc.python_method
    def mouseDidMove(self, notification):
        Glyphs.redraw()

    def mouseDown_(self, event):
        # if event.clickCount() == 3:
        #     self.mouseTripleDown_(event)
        #     return
        # if event.clickCount() == 2:
        #     self.mouseDoubleDown_(event)
        #     return
        if self.drag_start is None and self.active_metric is not None:
            self.dragging = True
            self.drag_start = self.mouse_position[0]

    def mouseUp_(self, event):
        self.dragging = False
        # Set changed metric
        if self.drag_start is None:
            return

        dist = self.getDraggedDistance()
        self.setMetrics(self.active_metric, dist)

        self.drag_start = None
