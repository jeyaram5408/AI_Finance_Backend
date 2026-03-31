# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from app.routers import feature_routes
# from app.routers import user_api
# from app.routers import transaction_routes, category_routes

# from app.core.exception_handlers import register_exception_handlers

# app = FastAPI()

# # CORS FIX
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],   # temporary allow all
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.get("/")
# def read_root():
#     return {"hello": "Hi"}

# register_exception_handlers(app)

# app.include_router(feature_routes.router)

# app.include_router(user_api.router)

# app.include_router(transaction_routes.router)
# app.include_router(category_routes.router)