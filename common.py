import base64
import logging

from abc import abstractmethod, ABC
from ctypes import *

import requests

logger = logging.getLogger()


class KeysStore(ABC):
    @abstractmethod
    def get_public_key(self) -> bytes:
        pass

    @abstractmethod
    def get_private_key(self) -> bytes:
        pass


class FsKeysStore(KeysStore):
    def __init__(self):
        self.__public_key = requests.get("https://lic.regulaforensics.com/getPK").content

    def get_private_key(self) -> bytes:
        return bytes()

    def get_public_key(self) -> bytes:
        return self.__public_key


class LicCrypto(ABC):
    @abstractmethod
    def encrypt(self, in_str: str) -> str:
        pass

    @abstractmethod
    def encrypt_binary(self, in_str: str) -> bytes:
        pass

    @abstractmethod
    def decrypt(self, in_str: str) -> str:
        pass

    @abstractmethod
    def decrypt_binary(self, in_data: bytes) -> str:
        pass

    @abstractmethod
    def sign(self, in_str) -> str: #type: ignore
        pass

    @abstractmethod
    def verify(self, in_str: str) -> str:
        pass

    @abstractmethod
    def unpack(self, in_data: bytes) -> str:
        pass


# noinspection PyProtectedMember
class LicCryptoLib(LicCrypto):
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    SIGN = "sign"
    VERIFY = "verify"

    def __init__(self, lib_secure, keys_store: KeysStore):
        self.__lib_secure = lib_secure
        self.__lib_secure._Enc.argtypes \
            = [POINTER(c_char), c_int, POINTER(c_char), c_int, POINTER(POINTER(c_char)), POINTER(c_int)]
        self.__lib_secure._Dec.argtypes \
            = [POINTER(c_char), c_int, POINTER(c_char), c_int, POINTER(POINTER(c_char)), POINTER(c_int)]
        self.__lib_secure._Sign.argtypes \
            = [POINTER(c_char), c_int, POINTER(c_char), c_int, POINTER(POINTER(c_char)), POINTER(c_int)]
        self.__lib_secure._Verify.argtypes \
            = [POINTER(c_char), c_int, POINTER(c_char), c_int, POINTER(POINTER(c_char)), POINTER(c_int)]
        self.__lib_secure._Unpack.argtypes = [POINTER(c_char), c_int]
        self.__lib_secure._Enc.restype = c_int
        self.__lib_secure._Dec.restype = c_int
        self.__lib_secure._Sign.restype = c_int
        self.__lib_secure._Verify.restype = c_int
        self.__lib_secure._Unpack.restype = POINTER(c_char)
        self.__lib_secure._Cleanup.argtypes = []
        self.__lib_secure._Cleanup.restype = None
        self.__lib_secure._Release.argtypes = [POINTER(c_char)]
        self.__lib_secure._Cleanup.restype = None
        self.__keys_store = keys_store

    def encrypt(self, in_str: str) -> str:
        out_data = self.encrypt_binary(in_str)
        enc_str = base64.b64encode(out_data).decode('utf-8')
        return enc_str

    def encrypt_binary(self, in_str: str) -> bytes:
        in_data = in_str.encode('utf-8')
        return self.__call_lib_func(self.ENCRYPT, in_data, self.__keys_store.get_public_key())

    def decrypt(self, in_str: str) -> str:
        in_data = base64.b64decode(in_str)
        return self.decrypt_binary(in_data)

    def decrypt_binary(self, in_data: bytes) -> str:
        out_data = self.__call_lib_func(
            self.DECRYPT,
            in_data,
            self.__keys_store.get_private_key())

        logger.debug(f'Decoded data - "{out_data}"')                #type: ignore
        out_str = out_data.decode('utf-8')
        return out_str

    def sign(self, _input) -> str:                                  #type: ignore
        if isinstance(_input, str):
            _input = _input.encode('utf-8')                         #type: ignore

        out_data = self.__call_lib_func(
            self.SIGN,
            _input,                                                 #type: ignore
            self.__keys_store.get_private_key())                    #type: ignore

        signed_str = base64.b64encode(out_data).decode('utf-8')
        return signed_str

    def verify(self, in_str: str) -> str:
        in_data = base64.b64decode(in_str)

        out_str = self.__call_lib_func(
            self.VERIFY,
            in_data,
            self.__keys_store.get_public_key()).decode('utf-8')

        return out_str

    def unpack(self, in_data: bytes) -> str:
        p_out_data = self.__lib_secure._Unpack(in_data, len(in_data))
        out_str = self.__c_char_pointer_to_string(p_out_data)
        self.__lib_secure._Release(p_out_data)

        return out_str

    def __call_lib_func(self, func_name: str, in_data: bytes, key: bytes) -> bytes:
        funcs = {
            self.ENCRYPT: self.__lib_secure._Enc,
            self.DECRYPT: self.__lib_secure._Dec,
            self.SIGN: self.__lib_secure._Sign,
            self.VERIFY: self.__lib_secure._Verify,
        }

        p_out_data = POINTER(c_char)()
        out_data_size = c_int()

        res = funcs[func_name](in_data, len(in_data), key, len(key), byref(p_out_data), byref(out_data_size))

        logger.debug(f'Call lib func, result code - {res}')

        self.__lib_secure._Cleanup()
        if res != 0:
            raise Exception(f'{func_name} error, Error code - {res}')

        out_data = p_out_data[:out_data_size.value]
        self.__lib_secure._Release(p_out_data)

        # noinspection PyTypeChecker
        return out_data                                                 #type: ignore

    @staticmethod
    def __c_char_pointer_to_string(ptr: POINTER(c_char)) -> str:        #type: ignore
        vp = cast(ptr, c_char_p).value
        if vp is None:
            return ''

        try:
            str_data = vp.decode('utf-8')
        except UnicodeDecodeError:
            str_data = vp.decode("cp1252")

        return str_data

