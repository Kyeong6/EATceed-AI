from fastapi import status

# 식습관 분석 API 응답 구성
get_user_analysis_responses = {
    401: {
        "description": "인증 오류: 잘못된 인증 토큰 또는 만료된 인증 토큰",
        "content": {
            "application/json": {
                "examples": {
                    "InvalidJWT": {
                        "summary": "잘못된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_1",
                                "reason": "잘못된 인증 토큰 형식입니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    },
                    "ExpiredJWT": {
                        "summary": "만료된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_2",
                                "reason": "인증 토큰이 만료되었습니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    }
                }
            }
        }
    },
    404: {
        "description": "데이터 오류: 회원 정보 또는 분석 데이터 없음",
        "content": {
            "application/json": {
                "examples": {
                    "MemberNotFound": {
                        "summary": "존재하지 않는 회원",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "MEMBER_400_9",
                                "reason": "존재하지 않는 회원입니다.",
                                "http_status": status.HTTP_404_NOT_FOUND
                            }
                        }
                    },
                    "UserDataError": {
                        "summary": "분석에 필요한 데이터 미존재(식사, 신체정보 등)",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "DIET_404_1",
                                "reason": "해당 유저의 분석에 필요한 데이터가 존재하지 않습니다.",
                                "http_status": status.HTTP_404_NOT_FOUND
                            }
                        }
                    },
                    "AnalysisNotCompleted": {
                        "summary": "분석 진행 중인 상태(현재 유저 분석 중이므로 미완료)",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "DIET_404_2",
                                "reason": "해당 유저에 대한 분석이 아직 완료되지 않았습니다.",
                                "http_status": status.HTTP_404_NOT_FOUND
                            }
                        }
                    },
                    "NoAnalysisRecord": {
                        "summary": "분석 기록 없음(해당 유저는 분석이 성공한 경우가 존재하지 않음)",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "DIET_404_3",
                                "reason": "해당 유저에 대한 분석 기록이 존재하지 않습니다.",
                                "http_status": status.HTTP_404_NOT_FOUND
                            }
                        }
                    }
                }
            }
        }
    },
    409: {
        "description": "분석 대기 중 상태 (다른 유저 분석 중)",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "response": None,
                    "error": {
                        "code": "DIET_409_1",
                        "reason": "해당 유저에 대한 분석 진행 대기 중입니다.",
                        "http_status": status.HTTP_409_CONFLICT
                    }
                }
            }
        }
    }
}

# 홈화면 분석 알림 API 응답 구성
get_status_alert_responses = {
    401: {
        "description": "인증 오류: 잘못된 인증 토큰 또는 만료된 인증 토큰",
        "content": {
            "application/json": {
                "examples": {
                    "InvalidJWT": {
                        "summary": "잘못된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_1",
                                "reason": "잘못된 인증 토큰 형식입니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    },
                    "ExpiredJWT": {
                        "summary": "만료된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_2",
                                "reason": "인증 토큰이 만료되었습니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    }
                }
            }
        }
    },
    404: {
        "description": "데이터 오류: 분석에 필요한 데이터 미존재 또는 분석 기록 없음",
        "content": {
            "application/json": {
                "examples": {
                    "UserDataError": {
                        "summary": "분석에 필요한 데이터 미존재(식사, 신체정보 등)",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "DIET_404_1",
                                "reason": "해당 유저의 분석에 필요한 데이터가 존재하지 않습니다.",
                                "http_status": status.HTTP_404_NOT_FOUND
                            }
                        }
                    },
                    "AnalysisNotCompleted": {
                        "summary": "분석 진행 중인 상태(현재 유저 분석 중이므로 미완료)",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "DIET_404_2",
                                "reason": "해당 유저에 대한 분석이 아직 완료되지 않았습니다.",
                                "http_status": status.HTTP_404_NOT_FOUND
                            }
                        }
                    },
                    "NoAnalysisRecord": {
                        "summary": "분석 기록 없음(해당 유저는 분석이 성공한 경우가 존재하지 않음)",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "DIET_404_3",
                                "reason": "해당 유저에 대한 분석 기록이 존재하지 않습니다.",
                                "http_status": status.HTTP_404_NOT_FOUND
                            }
                        }
                    }
                }
            }
        }
    },
    409: {
        "description": "분석 대기 중 상태 (다른 유저 분석 중)",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "response": None,
                    "error": {
                        "code": "DIET_409_1",
                        "reason": "해당 유저에 대한 분석 진행 대기 중입니다.",
                        "http_status": status.HTTP_409_CONFLICT
                    }
                }
            }
        }
    }
}


# 음식 이미지 분석 API 응답 구성
analyze_food_image_responses = {
    401: {
        "description": "인증 오류: 잘못된 인증 토큰 또는 만료된 인증 토큰",
        "content": {
            "application/json": {
                "examples": {
                    "InvalidJWT": {
                        "summary": "잘못된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_1",
                                "reason": "잘못된 인증 토큰 형식입니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    },
                    "ExpiredJWT": {
                        "summary": "만료된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_2",
                                "reason": "인증 토큰이 만료되었습니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    }
                }
            }
        }
    },
    429: {
        "description": "요청 제한 초과(5회)",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "response": None,
                    "error": {
                        "code": "IMAGE_429_1",
                        "reason": "하루 요청 제한을 초과했습니다.",
                        "http_status": status.HTTP_429_TOO_MANY_REQUESTS
                    }
                }
            }
        }
    },
    422: {
        "description": "이미지 처리 실패(multi-part 방식 수신 후 base64 인코딩)",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "response": None,
                    "error": {
                        "code": "IMAGE_422_1",
                        "reason": "이미지 처리 및 Base64 인코딩 중 오류가 발생했습니다.",
                        "http_status": status.HTTP_422_UNPROCESSABLE_ENTITY
                    }
                }
            }
        }
    },
    400: {
        "description": "잘못된 요청: 음식 이미지 오류 또는 API 분석 실패",
        "content": {
            "application/json": {
                "examples": {
                    "InvalidFoodImageError": {
                        "summary": "음식이 아닌 이미지를 업로드",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "IMAGE_400_2",
                                "reason": "음식이 아닌 이미지를 업로드하셨습니다.",
                                "http_status": status.HTTP_400_BAD_REQUEST
                            }
                        }
                    },
                    "ImageAnalysisError": {
                        "summary": "음식 이미지 분석 실패",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "IMAGE_400_1",
                                "reason": "OpenAI API를 이용한 음식 이미지를 분석할 수 없습니다.",
                                "http_status": status.HTTP_400_BAD_REQUEST
                            }
                        }
                    },
                    "InvalidFileFormat": {
                        "summary": "지원되지 않는 파일 형식",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "IMAGE_400_3",
                                "reason": "지원되지 않는 파일 형식: image/jpeg, image/png",
                                "http_status": status.HTTP_400_BAD_REQUEST
                            }
                        }
                    }
                }
            }
        }
    }
}

# 기능 잔여 횟수 확인 API 응답 구성
remaining_requests_check_responses = {
    401: {
        "description": "인증 오류: 잘못된 인증 토큰 또는 만료된 인증 토큰",
        "content": {
            "application/json": {
                "examples": {
                    "InvalidJWT": {
                        "summary": "잘못된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_1",
                                "reason": "잘못된 인증 토큰 형식입니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    },
                    "ExpiredJWT": {
                        "summary": "만료된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_2",
                                "reason": "인증 토큰이 만료되었습니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    }
                }
            }
        }
    }
}

# 이미지 검열 API 응답 구성
cencoring_image_responses = {
    401: {
        "description": "인증 오류: 잘못된 인증 토큰 또는 만료된 인증 토큰",
        "content": {
            "application/json": {
                "examples": {
                    "InvalidJWT": {
                        "summary": "잘못된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_1",
                                "reason": "잘못된 인증 토큰 형식입니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    },
                    "ExpiredJWT": {
                        "summary": "만료된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_2",
                                "reason": "인증 토큰이 만료되었습니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    }
                }
            }
        }
    },
    400: {
        "description": "잘못된 요청: 음식 이미지 오류 또는 API 분석 실패",
        "content": {
            "application/json": {
                "examples": {
                    "InvalidFileFormat": {
                        "summary": "지원되지 않는 파일 형식",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "IMAGE_400_3",
                                "reason": "지원되지 않는 파일 형식: image/jpeg, image/png",
                                "http_status": status.HTTP_400_BAD_REQUEST
                            }
                        }
                    }
                }
            }
        }
    }
}

# 식습관 분석 상세보기 API 응답 구성
get_detail_responses = {
    401: {
        "description": "인증 오류: 잘못된 인증 토큰 또는 만료된 인증 토큰",
        "content": {
            "application/json": {
                "examples": {
                    "InvalidJWT": {
                        "summary": "잘못된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_1",
                                "reason": "잘못된 인증 토큰 형식입니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    },
                    "ExpiredJWT": {
                        "summary": "만료된 인증 토큰",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "SECURITY_401_2",
                                "reason": "인증 토큰이 만료되었습니다.",
                                "http_status": status.HTTP_401_UNAUTHORIZED
                            }
                        }
                    }
                }
            }
        }
    },
    404: {
        "description": "데이터 오류: 분석에 필요한 데이터 미존재 또는 분석 기록 없음",
        "content": {
            "application/json": {
                "examples": {
                    "NoAnalysisRecord": {
                        "summary": "분석 기록 없음(해당 유저는 분석이 성공한 경우가 존재하지 않음)",
                        "value": {
                            "success": False,
                            "response": None,
                            "error": {
                                "code": "DIET_404_3",
                                "reason": "해당 유저에 대한 분석 기록이 존재하지 않습니다.",
                                "http_status": status.HTTP_404_NOT_FOUND
                            }
                        }
                    }
                }
            }
        }
    }
}