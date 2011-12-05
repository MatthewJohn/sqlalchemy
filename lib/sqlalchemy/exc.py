# sqlalchemy/exc.py
# Copyright (C) 2005-2011 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Exceptions used with SQLAlchemy.

The base exception class is :class:`.SQLAlchemyError`.  Exceptions which are raised as a
result of DBAPI exceptions are all subclasses of
:class:`.DBAPIError`.

"""

import traceback

class SQLAlchemyError(Exception):
    """Generic error class."""


class ArgumentError(SQLAlchemyError):
    """Raised when an invalid or conflicting function argument is supplied.

    This error generally corresponds to construction time state errors.

    """


class CircularDependencyError(SQLAlchemyError):
    """Raised by topological sorts when a circular dependency is detected.
    
    There are two scenarios where this error occurs:
    
    * In a Session flush operation, if two objects are mutually dependent
      on each other, they can not be inserted or deleted via INSERT or 
      DELETE statements alone; an UPDATE will be needed to post-associate
      or pre-deassociate one of the foreign key constrained values.
      The ``post_update`` flag described at :ref:`post_update` can resolve 
      this cycle.
    * In a :meth:`.MetaData.create_all`, :meth:`.MetaData.drop_all`,
      :attr:`.MetaData.sorted_tables` operation, two :class:`.ForeignKey`
      or :class:`.ForeignKeyConstraint` objects mutually refer to each
      other.  Apply the ``use_alter=True`` flag to one or both,
      see :ref:`use_alter`.
      
    """
    def __init__(self, message, cycles, edges):
        message += " Cycles: %r all edges: %r" % (cycles, edges)
        SQLAlchemyError.__init__(self, message)
        self.cycles = cycles
        self.edges = edges

class CompileError(SQLAlchemyError):
    """Raised when an error occurs during SQL compilation"""

class IdentifierError(SQLAlchemyError):
    """Raised when a schema name is beyond the max character limit"""

# Moved to orm.exc; compatibility definition installed by orm import until 0.6
ConcurrentModificationError = None

class DisconnectionError(SQLAlchemyError):
    """A disconnect is detected on a raw DB-API connection.

    This error is raised and consumed internally by a connection pool.  It can
    be raised by the :meth:`.PoolEvents.checkout` event 
    so that the host pool forces a retry; the exception will be caught
    three times in a row before the pool gives up and raises 
    :class:`~sqlalchemy.exc.InvalidRequestError` regarding the connection attempt.

    """


# Moved to orm.exc; compatibility definition installed by orm import until 0.6
FlushError = None

class TimeoutError(SQLAlchemyError):
    """Raised when a connection pool times out on getting a connection."""


class InvalidRequestError(SQLAlchemyError):
    """SQLAlchemy was asked to do something it can't do.

    This error generally corresponds to runtime state errors.

    """

class ResourceClosedError(InvalidRequestError):
    """An operation was requested from a connection, cursor, or other
    object that's in a closed state."""

class NoSuchColumnError(KeyError, InvalidRequestError):
    """A nonexistent column is requested from a ``RowProxy``."""

class NoReferenceError(InvalidRequestError):
    """Raised by ``ForeignKey`` to indicate a reference cannot be resolved."""

class NoReferencedTableError(NoReferenceError):
    """Raised by ``ForeignKey`` when the referred ``Table`` cannot be located."""

    def __init__(self, message, tname):
        NoReferenceError.__init__(self, message)
        self.table_name = tname

class NoReferencedColumnError(NoReferenceError):
    """Raised by ``ForeignKey`` when the referred ``Column`` cannot be located."""

    def __init__(self, message, tname, cname):
        NoReferenceError.__init__(self, message)
        self.table_name = tname
        self.column_name = cname

class NoSuchTableError(InvalidRequestError):
    """Table does not exist or is not visible to a connection."""


class UnboundExecutionError(InvalidRequestError):
    """SQL was attempted without a database connection to execute it on."""


class DontWrapMixin(object):
    """A mixin class which, when applied to a user-defined Exception class,
    will not be wrapped inside of :class:`.StatementError` if the error is
    emitted within the process of executing a statement.
    
    E.g.::
        from sqlalchemy.exc import DontWrapMixin
        
        class MyCustomException(Exception, DontWrapMixin):
            pass
        
        class MySpecialType(TypeDecorator):
            impl = String
            
            def process_bind_param(self, value, dialect):
                if value == 'invalid':
                    raise MyCustomException("invalid!")
            
    """
import sys
if sys.version_info < (2, 5):
    class DontWrapMixin:
        pass

# Moved to orm.exc; compatibility definition installed by orm import until 0.6
UnmappedColumnError = None

class StatementError(SQLAlchemyError):
    """An error occurred during execution of a SQL statement.
    
    :class:`.StatementError` wraps the exception raised
    during execution, and features :attr:`.statement`
    and :attr:`.params` attributes which supply context regarding
    the specifics of the statement which had an issue.

    The wrapped exception object is available in 
    the :attr:`.orig` attribute.
    
    """

    def __init__(self, message, statement, params, orig):
        SQLAlchemyError.__init__(self, message)
        self.statement = statement
        self.params = params
        self.orig = orig

    def __str__(self):
        from sqlalchemy.sql import util
        params_repr = util._repr_params(self.params, 10)
        return ' '.join((SQLAlchemyError.__str__(self),
                         repr(self.statement), repr(params_repr)))


class DBAPIError(StatementError):
    """Raised when the execution of a database operation fails.

    ``DBAPIError`` wraps exceptions raised by the DB-API underlying the
    database operation.  Driver-specific implementations of the standard
    DB-API exception types are wrapped by matching sub-types of SQLAlchemy's
    ``DBAPIError`` when possible.  DB-API's ``Error`` type maps to
    ``DBAPIError`` in SQLAlchemy, otherwise the names are identical.  Note
    that there is no guarantee that different DB-API implementations will
    raise the same exception type for any given error condition.

    :class:`.DBAPIError` features :attr:`.statement`
    and :attr:`.params` attributes which supply context regarding
    the specifics of the statement which had an issue, for the 
    typical case when the error was raised within the context of
    emitting a SQL statement.

    The wrapped exception object is available in the :attr:`.orig` attribute.
    Its type and properties are DB-API implementation specific.

    """

    @classmethod
    def instance(cls, statement, params, 
                        orig, 
                        dbapi_base_err,
                        connection_invalidated=False):
        # Don't ever wrap these, just return them directly as if
        # DBAPIError didn't exist.
        if isinstance(orig, (KeyboardInterrupt, SystemExit, DontWrapMixin)):
            return orig

        if orig is not None:
            # not a DBAPI error, statement is present.
            # raise a StatementError
            if not isinstance(orig, dbapi_base_err) and statement:
                return StatementError(
                            "%s (original cause: %s)" % (
                                str(orig), 
                                traceback.format_exception_only(orig.__class__, orig)[-1].strip()
                            ), statement, params, orig)

            name, glob = orig.__class__.__name__, globals()
            if name in glob and issubclass(glob[name], DBAPIError):
                cls = glob[name]

        return cls(statement, params, orig, connection_invalidated)

    def __init__(self, statement, params, orig, connection_invalidated=False):
        try:
            text = str(orig)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception, e:
            text = 'Error in str() of DB-API-generated exception: ' + str(e)
        StatementError.__init__(
                self, 
                '(%s) %s' % (orig.__class__.__name__, text),
                statement,
                params,
                orig
        )
        self.connection_invalidated = connection_invalidated


class InterfaceError(DBAPIError):
    """Wraps a DB-API InterfaceError."""


class DatabaseError(DBAPIError):
    """Wraps a DB-API DatabaseError."""


class DataError(DatabaseError):
    """Wraps a DB-API DataError."""


class OperationalError(DatabaseError):
    """Wraps a DB-API OperationalError."""


class IntegrityError(DatabaseError):
    """Wraps a DB-API IntegrityError."""


class InternalError(DatabaseError):
    """Wraps a DB-API InternalError."""


class ProgrammingError(DatabaseError):
    """Wraps a DB-API ProgrammingError."""


class NotSupportedError(DatabaseError):
    """Wraps a DB-API NotSupportedError."""


# Warnings

class SADeprecationWarning(DeprecationWarning):
    """Issued once per usage of a deprecated API."""


class SAPendingDeprecationWarning(PendingDeprecationWarning):
    """Issued once per usage of a deprecated API."""


class SAWarning(RuntimeWarning):
    """Issued at runtime."""
