from dataclasses import dataclass, asdict

from models import PidRecord, DocumentMetadata
from application.settings import PID_ADMIN_HANDLE, PID_ADMIN_HANDLE_INDEX, PID_ADMIN_VALUE_INDEX, PID_ADMIN_HANDLE_PERMISSIONS
from application.exceptions.types import IntegrityException
from services.pid.handle.base import HandleValue, HandleValueDataAdmin, HandleValueType, HandleValueObject, HandleValueDataFormat


class MetadataHandleValue(HandleValue):

    def __init__(self, index: int, type: HandleValueType, data_value: str):
        if type in [HandleValueType.HS_ADMIN, HandleValueType.HS_VLIST, HandleValueType.HS_PUBKEY]:
            raise AttributeError(f"Invalid type for MetadataHandleValue: {type}. HS_ADMIN, HS_VLIST, and HS_PUBKEY are not allowed.")
        data = HandleValueObject(
            format=HandleValueDataFormat.STRING,
            value=data_value
        )
        super().__init__(index=index, type=type, data=data)


class AdminHandleValue(HandleValue):

    def __init__(self, handle: str = PID_ADMIN_HANDLE, index: int = PID_ADMIN_HANDLE_INDEX, permissions: str = PID_ADMIN_HANDLE_PERMISSIONS):
        data = HandleValueObject(
            format=HandleValueDataFormat.ADMIN,
            value=HandleValueDataAdmin(
                handle=handle,
                index=index,
                permissions=permissions
            )
        )
        super().__init__(index=PID_ADMIN_VALUE_INDEX, type=HandleValueType.HS_ADMIN, data=data)


@dataclass
class HandleRecord:
    pid: str
    values: list[MetadataHandleValue]
    admin_value: AdminHandleValue

    @property
    def record_values(self) -> list[dict]:
        """
        Returns a dictionary representation of the handle record values.
        """
        values = [value.to_dict() for value in self.values]
        values.append(self.admin_value.to_dict())
        return values
    
    @classmethod
    def from_record_values(cls, pid: str, record_values: list[dict]) -> 'HandleRecord':
        """
        Converts a list of record values to a HandleRecord.
        """
        values = []
        admin_value = None
        for value in record_values:
            if value['type'] == HandleValueType.HS_ADMIN.value:
                admin_value = AdminHandleValue(
                    handle=value['data']['value']['handle'],
                    index=value['index'],
                    permissions=value['data']['value']['permissions']
                )
            else:
                handle_value_type = HandleValueType(value['type'])
                values.append(MetadataHandleValue(
                    index=value['index'],
                    type=handle_value_type,
                    data_value=value['data']['value']
                ))

        # TODO: check
        if not admin_value:
            admin_value = AdminHandleValue()

        return cls(pid=pid, values=values, admin_value=admin_value)

    @classmethod
    def from_pid_record(cls, pid_record: PidRecord) -> 'HandleRecord':
        """
        Converts a PidRecord to a HandleRecord.
        """
        values = []
        for idx, (attribute_name, attribute_value) in enumerate(pid_record.__dict__.items()):
            if attribute_name.startswith('_') or attribute_name == 'pid':
                continue
            if attribute_value is None:
                continue
            handle_value_type = HandleValueType.from_pid_record_attribute(attribute_name)
            values.append(MetadataHandleValue(
                index=idx,
                type=handle_value_type,
                data_value=str(attribute_value)
            ))
        if pid_record.other:
            for attribute_name, attribute_value in pid_record.other.items():
                if attribute_value is None:
                    continue
                handle_value_type = HandleValueType.from_pid_record_attribute(attribute_name)
                
                # Differentiate metadata indexes and leave space for other possible pid record values
                try:
                    metadata_index = list(DocumentMetadata.__dataclass_fields__.keys()).index(attribute_name)
                except ValueError:
                    raise IntegrityException(f"Record with PID {pid_record.pid} contains an invalid metadata attribute: {attribute_name}.")

                values.append(MetadataHandleValue(
                    index=30 + metadata_index,
                    type=handle_value_type,
                    data_value=str(attribute_value)
                ))

        return cls(pid=pid_record.pid, values=values, admin_value=AdminHandleValue())
    
    def to_pid_record(self) -> PidRecord:
        """
        Converts the HandleRecord back to a PidRecord.
        """
        pid_record_data = {value.type.value.lower(): (value.data if isinstance(value.data, str) else str(value.data.value)) for value in self.values}
        pid_record_data['pid'] = self.pid
        try:
            return PidRecord(**pid_record_data)
        except Exception as e:
            raise IntegrityException(f"Failed to convert properly the handle record with PID {self.pid}: {str(e)}") from e
