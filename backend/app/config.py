from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用配置
    app_name: str = "专利智能分析平台"
    app_version: str = "1.0.0"
    debug: bool = False

    # 服务器配置
    host : str = "0.0.0.0"
    port : int = 8000
    cors_origins: str = "*"
    
    # LLM配置
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    
    # 日志配置
    log_level: str = "INFO"

    def get_cors_origins_list(self):
        if not self.cors_origins:
            return ["*"]

        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return origins or ["*"]

settings = Settings()
def get_settings():
    return settings
    