package com.b2b.order.service;

import com.b2b.order.client.PartnerClient;
import com.b2b.order.entity.Order;
import com.b2b.order.repository.OrderRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@Transactional
public class OrderService {

    private final OrderRepository repo;
    private final PartnerClient partnerClient;

    public OrderService(OrderRepository repo, PartnerClient partnerClient) {
        this.repo = repo;
        this.partnerClient = partnerClient;
    }

    public Order create(Order order) {
        // REST call to partner-service — generates inter-service HTTP overhead
        partnerClient.getPartner(order.getPartnerId());
        return repo.save(order);
    }

    @Transactional(readOnly = true)
    public List<Order> findAll() {
        return repo.findAll();
    }

    @Transactional(readOnly = true)
    public Order findById(Long id) {
        return repo.findById(id).orElseThrow(() ->
                new RuntimeException("Order not found: " + id));
    }

    @Transactional(readOnly = true)
    public List<Order> findByPartnerId(Long partnerId) {
        return repo.findByPartnerId(partnerId);
    }

    public Order updateStatus(Long id, Order.OrderStatus status) {
        Order order = findById(id);
        order.setStatus(status);
        return repo.save(order);
    }

    public void delete(Long id) {
        repo.deleteById(id);
    }
}
