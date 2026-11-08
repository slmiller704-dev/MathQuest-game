    database.commit()
    database.refresh(profile)
    database.refresh(battle)

    return build_game_response(
        database=database,
        profile=profile,
        battle=battle,
        event="ability",
        message=message,
    )


@app.get("/api/profile")
def get_profile(
    request: Request,
    database: Session = Depends(get_db),
):
    profile_id = request.cookies.get(
        "mathquest_profile_id",
    )

    if not profile_id:
        raise HTTPException(
            status_code=404,
            detail="No MathQuest profile was found.",
        )

    profile = database.get(
        StudentProfile,
        profile_id,
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Student profile was not found.",
        )

    rewards = database.scalars(
        select(Reward)
        .where(
            Reward.student_id == profile.id,
        )
        .order_by(Reward.earned_at.desc())
        .limit(20)
    ).all()

    return {
        "profile": {
            "id": profile.id,
            "display_name": profile.display_name,
            "grade": profile.grade,
            "archetype": profile.archetype,
            "variant": profile.variant,
            "level": profile.level,
            "xp": profile.xp,
            "coins": profile.coins,
            "wins": profile.wins,
        },
        "mastery": mastery_dictionary(
            database=database,
            student_id=profile.id,
        ),
        "rewards": [
            {
                "title": reward.title,
                "type": reward.reward_type,
                "details": reward.details,
                "earned_at": reward.earned_at,
            }
            for reward in rewards
        ],
    }
