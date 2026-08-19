from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, roles, permissions, bus_companies,buses, seats,
    routes,trips, trip_seats,bookings, payments
)

# Main V1 Router
router = APIRouter(prefix="/api/v1")

# Include all endpoint routers
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(roles.router)
router.include_router(permissions.router)
router.include_router(bus_companies.router)
router.include_router(buses.router)
router.include_router(seats.router)
router.include_router(routes.router)
router.include_router(trips.router)
router.include_router(trip_seats.router)
router.include_router(bookings.router)
router.include_router(payments.router)