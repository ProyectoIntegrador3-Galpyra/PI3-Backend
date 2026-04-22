from enum import Enum


class RolUsuario(str, Enum):
    ADMIN = "ADMIN"
    PRODUCTOR = "PRODUCTOR"
    TECNICO = "TECNICO"


class EstadoGalpon(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    MANTENIMIENTO = "MANTENIMIENTO"


class TipoMovimientoAve(str, Enum):
    INGRESO = "INGRESO"
    MORTALIDAD = "MORTALIDAD"
    AJUSTE = "AJUSTE"


class EstadoLote(str, Enum):
    ACTIVO = "ACTIVO"
    CERRADO = "CERRADO"


class TipoEventoSanitario(str, Enum):
    VACUNACION = "VACUNACION"
    DIAGNOSTICO = "DIAGNOSTICO"
    TRATAMIENTO = "TRATAMIENTO"
    INSPECCION = "INSPECCION"


class EstadoSync(str, Enum):
    PENDIENTE = "PENDIENTE"
    PROCESADO = "PROCESADO"
    ERROR = "ERROR"


class EstadoInventarioFoto(str, Enum):
    PENDIENTE = "PENDIENTE"
    PROCESANDO = "PROCESANDO"
    PROCESADO = "PROCESADO"
    CONFIRMADO = "CONFIRMADO"
    ERROR = "ERROR"
