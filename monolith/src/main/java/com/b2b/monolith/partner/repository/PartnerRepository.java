package com.b2b.monolith.partner.repository;

import com.b2b.monolith.partner.entity.Partner;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PartnerRepository extends JpaRepository<Partner, Long> {
}
