import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_id: str
    api_hash: str
    handler: str = '.saveit'
    reaction: str = '🔥'
    session_name: str = 'save'
    download_path: str = '.downloads/'
    login_mode: str = 'phone'

    @classmethod
    def from_env(cls):
        load_dotenv(dotenv_path='.env')
        return cls(
            api_id=os.getenv('API_ID'),
            api_hash=os.getenv('API_HASH'),
            handler=os.getenv('HANDLER', '.saveit'),
            reaction=os.getenv('REACTION', '🔥'),
            session_name=os.getenv('SESSION_NAME', 'save'),
            download_path=os.getenv('DOWNLOAD_PATH', '.downloads/'),
            login_mode=os.getenv('LOGIN_MODE', 'phone').lower(),
        )
