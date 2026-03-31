# from fastapi import FastAPI, Request, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from starlette.middleware.base import BaseHTTPMiddleware


# from app.core.exception_handlers import register_exception_handlers

# from app.routers import user_api


# # ======================================== LOCAL HOST ===========================================

# app = FastAPI()


# # ------------------------- Middleware for Allowed Hosts and IPs ----------------------------

# class AllowedHostsAndIPsMiddleware(BaseHTTPMiddleware):
#     def __init__(self, app, allowed_hosts: list, allowed_ips: list):
#         super().__init__(app)
#         self.allowed_hosts = allowed_hosts
#         self.allowed_ips = allowed_ips

#     async def dispatch(self, request: Request, call_next):
#         # Skip host check if allowed_hosts contains "*"
#         host = request.headers.get("host")
#         if self.allowed_hosts != ["*"]:
#             if not host or host.split(":")[0] not in self.allowed_hosts:
#                 raise HTTPException(status_code=400, detail="Host not allowed")

#         # Skip IP check if allowed_ips contains "*"
#         client_ip = request.headers.get("x-forwarded-for")
#         if client_ip:
#             client_ip = client_ip.split(",")[0].strip()
#         else:
#             client_ip = request.client.host

#         if self.allowed_ips != ["*"] and client_ip not in self.allowed_ips:
#             raise HTTPException(status_code=403, detail="IP address not allowed")

#         response = await call_next(request)
#         return response


# allowed_hosts = ["*"]  # or simply skip the host check
# allowed_ips = ["*"]    # or skip IP check
# origins = [
#     "*",  # Allow all origins (for development only). In production, replace with specific frontend URL like "https://your-react-app.com"
# ]

# # Add CORS middleware first
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Add your custom Host/IP middleware next
# app.add_middleware(
#     AllowedHostsAndIPsMiddleware,
#     allowed_hosts=allowed_hosts,
#     allowed_ips=allowed_ips
# )



# # ------------------------- Error Handling ----------------------------

# register_exception_handlers(app)


# # ------------------------- Logging Configuration ----------------------------

# @app.get("/")
# def read_root():
#     return {"message": "Hello, World"}



# # ------------------------- ROUTERS ----------------------------

# # ------------------------- Users ----------------------------

# app.include_router(user_api.router)