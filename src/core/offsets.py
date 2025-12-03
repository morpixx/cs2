import requests
import logging

class Offsets:
    _URL_OFFSETS = "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json"
    _URL_CLIENT = "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json"

    dwLocalPlayerPawn = 0
    m_vOldOrigin = 0
    m_vecViewOffset = 0
    m_AimPunchAngle = 0
    m_modelState = 0
    m_pGameSceneNode = 0
    m_fFlags = 0
    m_iIDEntIndex = 0
    m_lifeState = 0
    m_iHealth = 0
    m_iTeamNum = 0
    dwEntityList = 0
    m_bDormant = 0
    m_iShotsFired = 0
    m_hPawn = 0
    dwLocalPlayerController = 0
    dwViewMatrix = 0
    dwViewAngles = 0
    m_entitySpottedState = 0
    m_Item = 0
    m_pClippingWeapon = 0
    m_AttributeManager = 0
    m_iItemDefinitionIndex = 0
    m_bIsScoped = 0
    m_flFlashDuration = 0
    m_iszPlayerName = 0
    dwPlantedC4 = 0
    dwGlobalVars = 0
    m_nBombSite = 0
    m_bBombDefused = 0
    m_vecAbsVelocity = 0
    m_flDefuseCountDown = 0
    m_flC4Blow = 0
    m_bBeingDefused = 0

    WeaponRecoilScale = 2.0
    m_nCurrentTickThisFrame = 0x34

    Bones = {
        "head": 6, "neck_0": 5, "spine_1": 4, "spine_2": 2, "pelvis": 0,
        "arm_upper_L": 8, "arm_lower_L": 9, "hand_L": 10,
        "arm_upper_R": 13, "arm_lower_R": 14, "hand_R": 15,
        "leg_upper_L": 22, "leg_lower_L": 23, "ankle_L": 24,
        "leg_upper_R": 25, "leg_lower_R": 26, "ankle_R": 27
    }

    @classmethod
    def update_offsets(cls):
        logger = logging.getLogger("Offsets")
        try:
            logger.info("Fetching latest offsets from GitHub...")
            offsets_json = requests.get(cls._URL_OFFSETS).json()
            client_json = requests.get(cls._URL_CLIENT).json()

            client_dll = offsets_json['client.dll']
            cls.dwLocalPlayerPawn = client_dll['dwLocalPlayerPawn']
            cls.dwEntityList = client_dll['dwEntityList']
            cls.dwLocalPlayerController = client_dll['dwLocalPlayerController']
            cls.dwViewMatrix = client_dll['dwViewMatrix']
            cls.dwViewAngles = client_dll['dwViewAngles']
            cls.dwPlantedC4 = client_dll['dwPlantedC4']
            cls.dwGlobalVars = client_dll['dwGlobalVars']

            classes = client_json['client.dll']['classes']
            cls.m_fFlags = classes['C_BaseEntity']['fields']['m_fFlags']
            cls.m_pGameSceneNode = classes['C_BaseEntity']['fields']['m_pGameSceneNode']
            cls.m_lifeState = classes['C_BaseEntity']['fields']['m_lifeState']
            cls.m_iHealth = classes['C_BaseEntity']['fields']['m_iHealth']
            cls.m_iTeamNum = classes['C_BaseEntity']['fields']['m_iTeamNum']
            cls.m_vecAbsVelocity = classes['C_BaseEntity']['fields']['m_vecAbsVelocity']
            
            cls.m_vOldOrigin = classes['C_BasePlayerPawn']['fields']['m_vOldOrigin']
            
            cls.m_vecViewOffset = classes['C_BaseModelEntity']['fields']['m_vecViewOffset']
            
            cls.m_AimPunchAngle = classes['C_CSPlayerPawn']['fields']['m_aimPunchAngle']
            cls.m_iIDEntIndex = classes['C_CSPlayerPawn']['fields']['m_iIDEntIndex']
            cls.m_iShotsFired = classes['C_CSPlayerPawn']['fields']['m_iShotsFired']
            cls.m_entitySpottedState = classes['C_CSPlayerPawn']['fields']['m_entitySpottedState']

            cls.m_pClippingWeapon = classes['C_CSPlayerPawn']['fields']['m_pClippingWeapon']
            cls.m_bIsScoped = classes['C_CSPlayerPawn']['fields']['m_bIsScoped']
            cls.m_flFlashDuration = classes['C_CSPlayerPawnBase']['fields']['m_flFlashDuration']
            
            cls.m_modelState = classes['CSkeletonInstance']['fields']['m_modelState']
            
            cls.m_bDormant = classes['CGameSceneNode']['fields']['m_bDormant']
            
            cls.m_hPawn = classes['CBasePlayerController']['fields']['m_hPawn']
            cls.m_iszPlayerName = classes['CBasePlayerController']['fields']['m_iszPlayerName']
            
            cls.m_Item = classes['C_AttributeContainer']['fields']['m_Item']
            
            cls.m_AttributeManager = classes['C_EconEntity']['fields']['m_AttributeManager']
            
            cls.m_iItemDefinitionIndex = classes['C_EconItemView']['fields']['m_iItemDefinitionIndex']
            
            cls.m_nBombSite = classes['C_PlantedC4']['fields']['m_nBombSite']
            cls.m_bBombDefused = classes['C_PlantedC4']['fields']['m_bBombDefused']
            cls.m_flDefuseCountDown = classes['C_PlantedC4']['fields']['m_flDefuseCountDown']
            cls.m_flC4Blow = classes['C_PlantedC4']['fields']['m_flC4Blow']
            cls.m_bBeingDefused = classes['C_PlantedC4']['fields']['m_bBeingDefused']

            logger.info("Offsets updated successfully!")
            return True

        except Exception as e:
            logger.error(f"Failed to update offsets: {e}")
            return False