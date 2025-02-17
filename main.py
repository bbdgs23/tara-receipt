# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import base64
import os
from dotenv import load_dotenv
from typing import Optional
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",    # Vite 개발 서버
        "https://i12c201.duckdns.org",  # 프로덕션 환경 (슬래시 제거)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/ocr")  # 엔드포인트 경로를 /api/ocr로 변경
async def ocr_endpoint(file: UploadFile = File(...)):
    # 파일 유효성 검사 강화
    allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식입니다.")
    
    # 파일 크기 제한 (예: 5MB)
    max_file_size = 5 * 1024 * 1024  # 5MB
    file_contents = await file.read()
    if len(file_contents) > max_file_size:
        raise HTTPException(status_code=400, detail="파일 크기가 너무 큽니다. 5MB 이하의 파일만 허용됩니다.")
    
    try:
        # 파일 읽기
        base64_image = base64.b64encode(file_contents).decode('utf-8')
        
        # 파일 형식 추출
        file_format = file.content_type.split("/")[1]
        
        # OCR API 요청 본문 구성
        request_body = {
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": int(datetime.now().timestamp() * 1000),
            "images": [
                {
                    "format": file_format,
                    "name": file.filename or "receipt_test",
                    "data": base64_image
                }
            ]
        }
        
        # 환경 변수 확인
        ocr_api_url = os.getenv("NAVER_OCR_INVOKE_URL")
        secret_key = os.getenv("NAVER_OCR_SECRET_KEY")
        
        if not ocr_api_url or not secret_key:
            raise HTTPException(
                status_code=500,
                detail="서버 환경 변수(NAVER_OCR_INVOKE_URL, NAVER_OCR_SECRET_KEY)가 설정되지 않았습니다."
            )
        
        # OCR API 호출
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ocr_api_url,
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    "X-OCR-SECRET": secret_key
                },
                timeout=30.0  # 타임아웃 설정 추가
            )
            
            response.raise_for_status()
            return response.json()
        
    except httpx.HTTPError as http_err:
        raise HTTPException(
            status_code=500,
            detail=f"OCR 요청 중 네트워크 오류 발생: {str(http_err)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"서버 내부 오류 발생: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
