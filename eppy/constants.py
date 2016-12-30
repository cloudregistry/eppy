""" EPP Result Codes """
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


EPP_OK = r'1000'

EPP_OK_PENDING = r'1001'

EPP_QUEUE_EMPTY = r'1300'

EPP_QUEUE_NOT_EMPTY = r'1301'

EPP_LOGOUT_OK = r'1500'

# command element that is not defined by EPP
EPP_UNKNOWN_CMD = r'2000'

# improperly formed command element
EPP_CMD_SYNTAX = r'2001'

# properly formed command element but the command cannot be executed
# due to a sequencing or context error, e.g. <logout> before <login>
EPP_CMD_USE = r'2002'

# command for which a required parameter value has not been provided
EPP_PARAM_MISSING = r'2003'

# command parameter whose value is outside the range of values specified by the protocol.
# The error value SHOULD be returned via a <value> element in the EPP response
EPP_PARAM_VALUE_RANGE = r'2004'

# command containing a parameter whose value is improperly formed.
# The error value SHOULD be returned via a <value> element in the EPP response
EPP_PARAM_VALUE_SYNTAX = r'2005'

# command element specifying a protocol version that is not implemented by
# the server.
EPP_UNIMPLEMENTED_PROTO_VER = r'2100'

# valid EPP command element that is not implemented by the server.
EPP_UNIMPLEMENTED_COMMAND = r'2101'

# valid EPP command element that contains a protocol option that is not
# implemented by the server
EPP_UNIMPLEMENTED_OPTION = r'2102'

# valid EPP command element that contains a protocol command extension
# that is not implemented by the server
EPP_UNIMPLEMENTED_EXTENSION = r'2103'

# attemps to execute a billable operation and the command cannot be
# completed due to a client-billing failure.
EPP_BILLING_FAIL = r'2104'

# object that is not eligible for renewal in accordance with server policy
EPP_INELIGIBLE_RENEW = r'2105'

# object that is not eligible for transfer in accordance with server policy
EPP_INELIGIBLE_TRANSFER = r'2106'

# error when validating client credentials
EPP_AUTHN_ERROR = r'2200'

# client-authorization error when executing a command. This error
# is used to note that a client lacks privileges to execute the requested command
EPP_AUTHORIZATION_ERROR = r'2201'

# invalid command authorization information when attempting
# to confirm authorization to execute a command.  This error
# is used to note that a client has the privileges required
# to execute the requested command, but the authorization
# information provided by the client does not match the
# authorization information archived by the server
EPP_INVALID_AUTH_INFO = r'2202'

# command to transfer an object that is pending transfer due to an earlier
# transfer request
EPP_OBJECT_PENDING_XFR = r'2300'

# received command to confirm, reject, or cancel the transfer of an
# object when no command has been made to transfer the object.
EPP_OBJECT_NOT_PENDING_XFR = r'2301'

# command to create an object that already exists in the repository
EPP_OBJECT_EXISTS = r'2302'

# command to query or transform an object that does not exist in the repository
EPP_OBJECT_DOES_NOT_EXIST = r'2303'

# command to transform an object that cannot be completed
# due to server policy or business practices.
EPP_OBJECT_STATUS = r'2304'

# command to transform an object that cannot be completed
# due to dependencies on other objects that are associated
# with the target object.
EPP_OBJECT_ASSOC = r'2305'

# command containing a parameter value that is syntactically valid
# but semantically invalid due to local policy.
# The error value SHOULD be returned via a <value> element in the EPP response.
EPP_PARAM_VALUE_POLICY = r'2306'

# a command to operate on an object service that is not supported by the server
EPP_UNIMPLEMENTED_OBJ_SVC = r'2307'

# command whose execution results in a violation of server data management policies
EPP_DATA_MGMT_POLICY = r'2308'

# unable to execute a command due to an internal server error
# that is not related to the protocol. The failure can be transient.
EPP_FAILED = r'2400'

# command that cannot be completed due to an internal server error
# that is not related to the protocol. The failure is not transient
# and will cause other commands to fail as well.
# The server MUST end the active session and close the existing connection.
EPP_FAILED_CLOSING = r'2500'

# error when validating client credentials and
# a server-defined limit on the number of allowable failures has been exceeded.
# The server MUST close the existing connection.
EPP_AUTH_FAILED_CLOSING = r'2501'

# <login> command that cannot be completed because the client has exceeded
# a system-defined limit on the number of sessions that the client can establish.
# It might be possible to establish a session by ending existing unused sessions
# and closing inactive connections.
EPP_AUTH_SESSION_LIMIT = r'2502'
