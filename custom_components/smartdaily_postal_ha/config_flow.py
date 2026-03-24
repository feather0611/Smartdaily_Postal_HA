import voluptuous as vol
import logging
from homeassistant import config_entries
from homeassistant.core import callback
import requests
import aiohttp

_LOGGER = logging.getLogger(__name__)

DOMAIN = "smartdaily_postal_ha"
KingnetAuthValue = ""


class MyParcelTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """smartdaily_postal_ha config flow."""

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            self.device_id = user_input["DeviceID"]  # 获取DeviceID的值
            url = (
                "https://api.smartdaily.com.tw/api/Valid/getHashCodeV2?code="
                + self.device_id
            )
            headers = {
                "Connection": "keep-alive",
                "Accept": "application/json, text/plain, */*"
            }
            response = await self.hass.async_add_executor_job(
                requests.get, url, headers
            )
            if response.status_code == 200:
                # 解析JSON數據
                data = response.json()
                self.KingnetAuthValue = "CommunityUser " + data["Data"]["token"]
                _LOGGER.debug("Token updated successfully") 
                
            else:
                _LOGGER.error("Token request failed, status code: %s", response.status_code)
            # 尝试使用DeviceID获取KingnetAuth令牌和社区列表
            # 这里需要添加逻辑来调用API
            # ...

            # 假设成功，转到社区选择步骤
            return await self.async_step_select_community()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("DeviceID"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_community(self, user_input=None):
        """Handle the step to select a community."""
        errors = {}
        if user_input is not None:
            # 用户已选择社区，存储选定的社区ID并创建配置条目
            return self.async_create_entry(
                title="My Parcel Tracker",
                data={"DeviceID": self.device_id, "com_id": user_input["com_id"]},
            )

        # 获取社区列表并生成选项
        communities = await self._get_communities(self.KingnetAuthValue)
        options = {com["id"]: com["community"] for com in communities}

        return self.async_show_form(
            step_id="select_community",
            data_schema=vol.Schema(
                {
                    vol.Required("com_id", description="選擇社區"): vol.In(options),
                }
            ),
            errors=errors,
        )

    async def _get_communities(self, KingnetAuthValue):
        """获取社区列表。"""
        headers = {
            "Connection": "keep-alive",
            "KingnetAuth": self.KingnetAuthValue,
            "Accept": "application/json, text/plain, */*"
        }
        communities = []
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.smartdaily.com.tw/api/Community/GetUserCommunityList",
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    for com in data["Data"]:
                        communities.append(
                            {"id": com["id"], "community": com["community"]}
                        )
                else:
                    text = await response.text()
                    _LOGGER.error("Community list request failed, status code: %s, response: %s", response.status, text)

        return communities
