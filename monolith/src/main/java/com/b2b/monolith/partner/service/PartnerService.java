package com.b2b.monolith.partner.service;

import com.b2b.monolith.partner.entity.Partner;
import com.b2b.monolith.partner.repository.PartnerRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@Transactional
public class PartnerService {

    private final PartnerRepository repo;

    public PartnerService(PartnerRepository repo) {
        this.repo = repo;
    }

    public Partner create(Partner partner) {
        return repo.save(partner);
    }

    @Transactional(readOnly = true)
    public List<Partner> findAll() {
        return repo.findAll();
    }

    @Transactional(readOnly = true)
    public Partner findById(Long id) {
        return repo.findById(id).orElseThrow(() ->
                new RuntimeException("Partner not found: " + id));
    }

    public Partner update(Long id, Partner updated) {
        Partner existing = findById(id);
        existing.setName(updated.getName());
        existing.setEmail(updated.getEmail());
        existing.setPhone(updated.getPhone());
        existing.setAddress(updated.getAddress());
        existing.setTaxId(updated.getTaxId());
        return repo.save(existing);
    }

    public void delete(Long id) {
        repo.deleteById(id);
    }
}
