#!/usr/bin/env python

##############################################################################
##
## This file is part of Sardana
##
## http://www.tango-controls.org/static/sardana/latest/doc/html/index.html
##
## Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
##
## Sardana is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Sardana is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with Sardana.  If not, see <http://www.gnu.org/licenses/>.
##
##############################################################################

""" """

__all__ = ["ZeroDExpChannel", "ZeroDExpChannelClass"]

__docformat__ = 'restructuredtext'

import time

from PyTango import Except
from PyTango import DevVoid, DevDouble, DevString
from PyTango import DispLevel, DevState, AttrQuality
from PyTango import READ, READ_WRITE, SCALAR, SPECTRUM

from taurus.core.util.log import DebugIt

from sardana import State, SardanaServer
from sardana.sardanaattribute import SardanaAttribute

from PoolDevice import PoolElementDevice, PoolElementDeviceClass


class ZeroDExpChannel(PoolElementDevice):

    def __init__(self, dclass, name):
        PoolElementDevice.__init__(self, dclass, name)
        ZeroDExpChannel.init_device(self)

    def init(self, name):
        PoolElementDevice.init(self, name)

    def get_zerod(self):
        return self.element

    def set_zerod(self, zerod):
        self.element = zerod

    zerod = property(get_zerod, set_zerod)

    @DebugIt()
    def delete_device(self):
        PoolElementDevice.delete_device(self)

    @DebugIt()
    def init_device(self):
        PoolElementDevice.init_device(self)

        detect_evts = "state", "value"
        non_detect_evts = ()
        self.set_change_events(detect_evts, non_detect_evts)

        if self.zerod is None:
            full_name = self.get_full_name()
            name = self.alias or full_name
            zerod = self.pool.create_element(type="ZeroDExpChannel", name=name,
                full_name=full_name, id=self.Id, axis=self.Axis,
                ctrl_id=self.Ctrl_id)
            zerod.add_listener(self.on_zerod_changed)
            self.zerod = zerod
        # force a state read to initialize the state attribute
        state = self.zerod.state

    def on_zerod_changed(self, event_source, event_type, event_value):
        # during server startup and shutdown avoid processing element
        # creation events
        if SardanaServer.server_state != State.Running:
            return

        timestamp = time.time()
        name = event_type.name
        quality = AttrQuality.ATTR_VALID
        priority = event_type.priority
        error = None
        attr = self.get_device_attr().get_attr_by_name(name)

        if name == "state":
            event_value = self.calculate_tango_state(event_value)
        elif name == "status":
            event_value = self.calculate_tango_status(event_value)
        else:
            if isinstance(event_value, SardanaAttribute):
                if event_value.error:
                    error = Except.to_dev_failed(*event_value.exc_info)
                timestamp = event_value.timestamp
                event_value = event_value.value

            if name == "value":
                state = self.zerod.get_state()
                if state == State.Moving:
                    quality = AttrQuality.ATTR_CHANGING
        self.set_attribute(attr, value=event_value, timestamp=timestamp,
                           quality=quality, priority=priority, error=error,
                           synch=False)

    def always_executed_hook(self):
        #state = to_tango_state(self.zerod.get_state(cache=False))
        pass

    def read_attr_hardware(self,data):
        pass

    def read_Value(self, attr):
        zerod = self.zerod
        value = zerod.get_value()
        quality = None
        if self.get_state() == DevState.MOVING:
            quality = AttrQuality.ATTR_CHANGING
        self.set_attribute(attr, value=value, quality=quality, priority=0)

    def read_CurrentValue(self, attr):
        val, exc_info = self.zerod.read_value()
        if exc_info is not None:
            Except.throw_python_exception(*exc_info)
        self.set_attribute(attr, value=val, priority=0)

    def Start(self):
        self.zerod.start_acquisition()

    def read_ValueBuffer(self, attr):
        attr.set_value(self.zerod.get_value_buffer())

    def read_TimeBuffer(self, attr):
        attr.set_value(self.zerod.get_time_buffer())

    def read_CumulationType(self, attr):
        attr.set_value(self.zerod.get_cumulation_type())

    def write_CumulationType(self, attr):
        self.zerod.set_cumulation_type(attr.get_write_value())

    def _is_allowed(self, req_type):
        return PoolElementDevice._is_allowed(self, req_type)

    is_Value_allowed = _is_allowed
    is_CurrentValue_allowed = _is_allowed
    is_CumulationType_allowed = _is_allowed
    is_ValueBuffer_allowed = _is_allowed
    is_TimeBuffer_allowed = _is_allowed


class ZeroDExpChannelClass(PoolElementDeviceClass):

    #    Class Properties
    class_property_list = {
    }

    #    Device Properties
    device_property_list = {
    }
    device_property_list.update(PoolElementDeviceClass.device_property_list)

    #    Command definitions
    cmd_list = {
        'Start' :   [ [DevVoid, ""], [DevVoid, ""] ],
    }
    cmd_list.update(PoolElementDeviceClass.cmd_list)

    #    Attribute definitions
    attr_list = {
        'Value'          : [ [ DevDouble, SCALAR, READ ],
                             { 'abs_change'     : "1.0" } ],
        'CurrentValue'   : [ [ DevDouble, SCALAR, READ ],
                             { 'abs_change'     : "1.0" } ],
        'ValueBuffer'    : [ [ DevDouble, SPECTRUM, READ, 16384 ] ],
        'TimeBuffer'     : [ [ DevDouble, SPECTRUM, READ, 16384 ] ],
        'CumulationType' : [ [ DevString, SCALAR, READ_WRITE ],
                             { 'Memorized'     : "true",
                               'label'         : "Cumulation Type",
                               'Display level' : DispLevel.EXPERT } ],
    }
    attr_list.update(PoolElementDeviceClass.attr_list)

    def _get_class_properties(self):
        ret = PoolElementDeviceClass._get_class_properties(self)
        ret['Description'] = "0D experimental channel device class"
        ret['InheritedFrom'].insert(0, 'PoolElementDevice')
        return ret
